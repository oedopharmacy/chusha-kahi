"""ChatGPT (gpt-4o) で告示136カテゴリをバッチ検証。Gemini版の twin。

Output:
  data/gpt_verification.json  カテゴリ別の検証結果
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATS = ROOT / "data/kokuji_categories.json"
KOKUJI_RAW = ROOT / "data/kokuji_dai10_raw.txt"
MASTER = ROOT / "data/master.csv"
OUT = ROOT / "data/gpt_verification.json"

PROMPT_HEADER = """あなたは日本の医療・診療報酬制度の専門家です。以下は「療担規則及び薬担規則並びに療担基準に基づき厚生労働大臣が定める掲示事項等（平成18年厚生労働省告示第107号）第十第一号」に列挙された薬剤カテゴリです。

【前提】
- 使用シーン: 在宅専門クリニックの患者宅に**訪問薬局が訪問**し、**医師が患家で使用する**前提
- 問い: 「院外処方箋でこのカテゴリの薬剤を**訪問薬局経由で**処方できるか」

【判定区分】
- "○": 無条件で院外処方可能（告示に具体記載があり、条件付かない）
- "△": 条件付きで可能（在宅血液透析患者限定、特定疾患限定、用途限定 等）or 薬効分類名包括記載で個別品目の判定要
- "×": 院外処方不可（告示非該当）

【告示原文全体】
"""

PROMPT_BATCH_INSTRUCTION = """
【指示】
以下の各カテゴリについて、**JSON配列形式のみ**で回答してください（前後に説明文不要）。

```json
[
  {{
    "name": "カテゴリ名（入力そのまま）",
    "verdict": "○|△|×",
    "reason_why": "判定理由（80-150字、簡潔に）",
    "prescription_method": "△の場合のみ: 可能な処方方法（条件、必要な管理料、患者要件、処方箋記載要件 等を100-250字で具体的に）。○/×はnull",
    "source_text": "告示第十第一号の該当原文を verbatim 引用（30-150字）"
  }},
  ...
]
```

判定で確信が持てない場合のみ "△" にしてください。なるべく "○" か "×" を選択し、可否を明確化してください。

【入力カテゴリ ({n_cats}件)】
{cat_blocks}
"""


def log(msg: str) -> None:
    print(f"[gpt-batch] {msg}", flush=True)


def load_samples_and_claude_verdicts() -> tuple[dict, dict]:
    samples = defaultdict(list)
    verdicts = defaultdict(Counter)
    with MASTER.open(encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            reason = r["判定根拠"]
            if "[" not in reason or "]" not in reason:
                continue
            inner = reason.split("[", 1)[1].split("]", 1)[0]
            for cat in inner.split("/"):
                cat = cat.strip()
                if r["成分名"] not in samples[cat] and len(samples[cat]) < 4:
                    samples[cat].append(r["成分名"])
                verdicts[cat][r["院外処方可否"]] += 1
    return dict(samples), {cat: c.most_common(1)[0][0] for cat, c in verdicts.items()}


def ask_gpt(prompt: str, model: str) -> str:
    env = os.environ.copy()
    env["GPT_MODEL"] = model
    env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"
    result = subprocess.run(
        ["ask-gpt"], input=prompt, capture_output=True, text=True, env=env, timeout=300
    )
    if result.returncode != 0:
        raise RuntimeError(f"GPT error rc={result.returncode}: {result.stderr.strip()[:600]}")
    return result.stdout.strip()


def parse_batch(resp: str) -> list:
    s = resp.strip()
    if s.startswith("```"):
        s = s[s.find("\n") + 1 :]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
    start = s.find("[")
    end = s.rfind("]")
    if start < 0 or end < 0:
        raise ValueError(f"JSON array not found: {resp[:300]}")
    return json.loads(s[start : end + 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=3.0)
    ap.add_argument("--max-calls", type=int, default=20)
    args = ap.parse_args()

    cats = json.loads(CATS.read_text(encoding="utf-8"))
    kokuji_text = KOKUJI_RAW.read_text(encoding="utf-8")
    samples, claude_verdicts = load_samples_and_claude_verdicts()

    results = {}
    if OUT.exists():
        try:
            results = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            results = {}
    results = {k: v for k, v in results.items() if v.get("verdict")}

    todo = [c for c in cats if c["name"] not in results]
    log(f"未検証: {len(todo)}")
    if not todo:
        log("全件完了済")
        return 0

    batches = [todo[i : i + args.batch_size] for i in range(0, len(todo), args.batch_size)]
    log(f"バッチ数: {len(batches)} (max {args.max_calls})")

    calls = 0
    for bi, batch in enumerate(batches):
        if calls >= args.max_calls:
            log(f"max-calls 到達 ({calls})")
            break
        cat_blocks = []
        for c in batch:
            name = c["name"]
            cond = c.get("condition") or "なし"
            cv = claude_verdicts.get(name, "?")
            sample_ing = samples.get(name, [])
            cat_blocks.append(
                f"---\nカテゴリ名: {name}\n告示上の条件: {cond}\n"
                f"該当成分例: {'、'.join(sample_ing) if sample_ing else 'マッチなし'}\n"
                f"現行Claude判定: {cv}\n"
            )
        prompt = (
            PROMPT_HEADER + kokuji_text + "\n\n"
            + PROMPT_BATCH_INSTRUCTION.format(n_cats=len(batch), cat_blocks="\n".join(cat_blocks))
        )
        log(f"[{bi+1}/{len(batches)}] {len(batch)} cats ({batch[0]['name'][:25]}...)")
        try:
            raw = ask_gpt(prompt, model=args.model)
            parsed = parse_batch(raw)
            input_names = {c["name"] for c in batch}
            for item in parsed:
                name = item.get("name", "").strip()
                if name not in input_names:
                    for cand in input_names:
                        if cand in name or name in cand:
                            name = cand
                            break
                if name in input_names:
                    cv = claude_verdicts.get(name, "?")
                    results[name] = {
                        "verdict": item.get("verdict"),
                        "reason_why": item.get("reason_why", ""),
                        "prescription_method": item.get("prescription_method"),
                        "source_text": item.get("source_text", ""),
                        "claude_verdict": cv,
                    }
            log(f"  parsed {len(parsed)}")
            calls += 1
        except Exception as e:
            log(f"  ! ERROR: {e}")
            calls += 1
            if "RESOURCE" in str(e) or "429" in str(e) or "rate" in str(e).lower():
                break
        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        if bi < len(batches) - 1 and args.sleep > 0:
            time.sleep(args.sleep)

    log(f"\n完了: {len(results)}/{len(cats)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
