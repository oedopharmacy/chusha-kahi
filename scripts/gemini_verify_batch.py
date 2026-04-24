"""バッチ版: 10カテゴリを1APIコールで検証（無料枠の節約）。

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
OUT = ROOT / "data/gemini_verification.json"

PROMPT_HEADER = """あなたは日本の医療・診療報酬制度の専門家です。以下は「療担規則及び薬担規則並びに療担基準に基づき厚生労働大臣が定める掲示事項等（平成18年厚生労働省告示第107号）第十第一号」に列挙された薬剤カテゴリです。

【前提】
- 使用シーン: 在宅専門クリニックの患者宅に訪問薬局が訪問し、医師が患家で使用
- 問い: 「院外処方箋でこのカテゴリの薬剤を処方してよいか」

【判定区分】
- "○": 無条件で院外処方可能（告示に具体的記載）
- "△": 条件付き or 薬効分類名包括記載のため個別確認要
- "×": 院外処方不可（告示非該当）

【告示原文全体】
"""

PROMPT_BATCH_INSTRUCTION = """
【各カテゴリ情報】
以下に{n_cats}カテゴリ分の情報を提示します。各カテゴリについて、以下JSON配列形式**のみ**で回答してください（他の説明は不要）。

```json
[
  {{
    "name": "カテゴリ名（入力そのまま）",
    "verdict": "○|△|×",
    "reason_why": "判定理由の簡潔な説明（60-120字）",
    "prescription_method": "△の場合のみ: 条件や必要な管理料・処方箋記載要件など（80-200字）。○/×はnull",
    "source_text": "告示第十第一号の該当原文を verbatim 引用（30-120字）"
  }},
  ...
]
```

【入力カテゴリ一覧】
{cat_blocks}
"""


def log(msg: str) -> None:
    print(f"[batch] {msg}", flush=True)


def load_samples_and_claude_verdicts() -> tuple[dict, dict]:
    from collections import Counter as Ctr
    samples = defaultdict(list)
    verdicts = defaultdict(Ctr)
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
    verdict_map = {cat: c.most_common(1)[0][0] for cat, c in verdicts.items()}
    return dict(samples), verdict_map


def ask_gemini(prompt: str, model: str) -> str:
    env = os.environ.copy()
    env["GEMINI_MODEL"] = model
    env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"
    result = subprocess.run(
        ["ask-gemini"],
        input=prompt,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    if result.returncode != 0:
        err = result.stderr.strip()[:600]
        raise RuntimeError(f"Gemini error rc={result.returncode}: {err}")
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
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=15.0)
    ap.add_argument("--max-calls", type=int, default=20, help="この実行で使うAPIコール上限")
    args = ap.parse_args()

    cats = json.loads(CATS.read_text(encoding="utf-8"))
    kokuji_text = KOKUJI_RAW.read_text(encoding="utf-8")
    samples, claude_verdicts = load_samples_and_claude_verdicts()

    # Load existing
    results = {}
    if OUT.exists():
        results = json.loads(OUT.read_text(encoding="utf-8"))

    # Clean error entries
    results = {k: v for k, v in results.items() if v.get("verdict") and "error" not in v}

    # Find unverified categories
    todo = [c for c in cats if c["name"] not in results]
    log(f"未検証: {len(todo)}カテゴリ")
    if not todo:
        log("全カテゴリ検証済み")
        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    # Batch
    batches = [todo[i : i + args.batch_size] for i in range(0, len(todo), args.batch_size)]
    log(f"バッチ数: {len(batches)} (max {args.max_calls} まで実行)")

    calls_made = 0
    for bi, batch in enumerate(batches):
        if calls_made >= args.max_calls:
            log(f"max-calls 到達で中断 ({calls_made} calls)")
            break

        cat_blocks = []
        for c in batch:
            name = c["name"]
            cond = c.get("condition") or "なし"
            cv = claude_verdicts.get(name, "?")
            sample_ing = samples.get(name, [])
            cat_blocks.append(
                f"---\n"
                f"カテゴリ名: {name}\n"
                f"告示上の条件: {cond}\n"
                f"該当成分例（Claude突合結果）: {'、'.join(sample_ing) if sample_ing else 'マッチなし'}\n"
                f"現行ツール判定: {cv}\n"
            )

        prompt = (
            PROMPT_HEADER
            + kokuji_text
            + "\n\n"
            + PROMPT_BATCH_INSTRUCTION.format(
                n_cats=len(batch), cat_blocks="\n".join(cat_blocks)
            )
        )

        log(f"[{bi+1}/{len(batches)}] batch {len(batch)} cats ({batch[0]['name'][:20]}...)")
        try:
            raw = ask_gemini(prompt, model=args.model)
            parsed = parse_batch(raw)
            log(f"  parsed {len(parsed)} items")
            # Match back to input categories by name
            input_names = {c["name"] for c in batch}
            for item in parsed:
                name = item.get("name", "").strip()
                if name not in input_names:
                    # Try fuzzy match
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
                        "agrees": item.get("verdict") == cv,
                    }
            calls_made += 1
        except Exception as e:
            log(f"  ! ERROR: {e}")
            calls_made += 1  # エラーもコール数として数える（quota節約）
            # If quota error, stop
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                log("quota error: 中断")
                break

        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

        if bi < len(batches) - 1 and args.sleep > 0:
            time.sleep(args.sleep)

    # Summary
    total = len(results)
    agreeing = sum(1 for v in results.values() if v.get("agrees"))
    log(f"\n完了: 検証済 {total}/{len(cats)} カテゴリ, 一致{agreeing}")
    disagreements = [(n, v) for n, v in results.items() if v.get("verdict") and not v.get("agrees")]
    log(f"相違: {len(disagreements)}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
