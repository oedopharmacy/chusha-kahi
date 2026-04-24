"""Gemini を使って告示107号第十第一号の各カテゴリ判定を検証・解説付け。

Input:
  data/kokuji_categories.json    136 カテゴリ + 条件
  data/kokuji_dai10_raw.txt      告示原文
  data/category_rules.yaml       YJ4マッピング
  data/master.csv                Claude判定結果

Output:
  data/gemini_verification.json  カテゴリごとの検証結果
    {
      "category_name": {
        "verdict": "○|△|×",            # Gemini判定
        "claude_verdict": "○|△|×",     # Claude判定（現行）
        "agrees": bool,                  # 一致するか
        "reason_why": "...",             # 判定理由（100字程度）
        "prescription_method": "..."|null, # △の場合の処方方法
        "source_text": "...",            # 告示原文の該当部分
        "raw_response": "..."            # Gemini生レスポンス（デバッグ用）
      }, ...
    }

実行:
  .venv/bin/python3 scripts/gemini_verify.py           # 全カテゴリ
  .venv/bin/python3 scripts/gemini_verify.py --limit 5 # 先頭5件のみ（テスト）
  .venv/bin/python3 scripts/gemini_verify.py --resume  # 既存結果に追記（再開用）
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATS = ROOT / "data/kokuji_categories.json"
KOKUJI_RAW = ROOT / "data/kokuji_dai10_raw.txt"
MASTER = ROOT / "data/master.csv"
OUT = ROOT / "data/gemini_verification.json"

PROMPT_TEMPLATE = """あなたは日本の医療・診療報酬制度の専門家です。以下は「療担規則及び薬担規則並びに療担基準に基づき厚生労働大臣が定める掲示事項等（平成18年厚生労働省告示第107号）第十第一号」に列挙された薬剤カテゴリです。

【前提】
- このカテゴリは「保険医が投与することができる注射薬」として告示に列挙
- 使用シーン: 在宅専門クリニックの患者宅に訪問薬局が訪問し、医師が患家で使用
- 問いは「院外処方箋でこのカテゴリの薬剤を処方してよいか」

【判定区分】
- "○": 無条件で院外処方可能（告示に具体的記載）
- "△": 条件付きで可能（告示に条件文記載 or 薬効分類名で包括記載のため個別確認要）
- "×": 院外処方不可（告示非該当）

【カテゴリ情報】
- 名称: {category_name}
- 告示上の条件: {condition}
- 該当成分例（薬価基準注射薬データより）: {sample_ingredients}
- 現行ツール（Claude）の判定: {claude_verdict}

【告示原文（該当部分周辺）】
{kokuji_excerpt}

【指示】
以下のJSON形式**のみ**で回答してください（前後に説明文を付けない）。

```json
{{
  "verdict": "○または△または×",
  "reason_why": "判定理由の簡潔な説明（80-150字）",
  "prescription_method": "△の場合のみ: 可能な処方方法（算定すべき管理料、必要な患者要件、処方箋記載要件など、100-250字）。○か×の場合は null",
  "source_text": "告示第十第一号の該当原文を verbatim で引用（該当部分周辺も含め30-200字）"
}}
```

厳格にJSONのみ返答してください。Markdownコードブロック(```)は省略可。"""


def log(msg: str) -> None:
    print(f"[gemini_verify] {msg}", flush=True)


def load_categories() -> list[dict]:
    return json.loads(CATS.read_text(encoding="utf-8"))


def load_kokuji_raw() -> str:
    return KOKUJI_RAW.read_text(encoding="utf-8")


def load_sample_ingredients(limit: int = 5) -> dict[str, list[str]]:
    """カテゴリ名 → 該当成分名（最大limit件）"""
    samples = defaultdict(list)
    with MASTER.open(encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            reason = r["判定根拠"]
            # "[カテゴリ名]" を抽出
            if "[" not in reason or "]" not in reason:
                continue
            inner = reason.split("[", 1)[1].split("]", 1)[0]
            cats_here = inner.split("/")
            sei = r["成分名"]
            for cat in cats_here:
                cat = cat.strip()
                if sei not in samples[cat] and len(samples[cat]) < limit:
                    samples[cat].append(sei)
    return dict(samples)


def load_claude_verdicts() -> dict[str, str]:
    """カテゴリ名 → Claude判定（代表判定、カテゴリ内の最頻値）"""
    from collections import Counter
    verdicts = defaultdict(Counter)
    with MASTER.open(encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            reason = r["判定根拠"]
            if "[" not in reason or "]" not in reason:
                continue
            inner = reason.split("[", 1)[1].split("]", 1)[0]
            for cat in inner.split("/"):
                verdicts[cat.strip()][r["院外処方可否"]] += 1
    return {cat: c.most_common(1)[0][0] for cat, c in verdicts.items()}


def build_kokuji_excerpt(category_name: str, full_text: str, span: int = 250) -> str:
    """告示原文からカテゴリ周辺を抜粋"""
    idx = full_text.find(category_name)
    if idx < 0:
        # ルビ除去版で再検索
        normalized = category_name.replace("かん", "").replace("か", "")
        idx = full_text.find(normalized)
    if idx < 0:
        return "(該当部分の原文抽出失敗)"
    start = max(0, idx - span // 2)
    end = min(len(full_text), idx + len(category_name) + span // 2)
    return full_text[start:end].strip()


def ask_gemini(prompt: str, model: str = "gemini-2.5-flash") -> str:
    """ask-gemini CLI を呼び出し"""
    env = os.environ.copy()
    env["GEMINI_MODEL"] = model
    env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"
    result = subprocess.run(
        ["ask-gemini"],
        input=prompt,
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )
    if result.returncode != 0:
        err = result.stderr.strip()[:500]
        raise RuntimeError(f"Gemini error (rc={result.returncode}): {err}")
    return result.stdout.strip()


def parse_gemini_response(resp: str) -> dict:
    """GeminiレスポンスからJSON部分を抽出"""
    s = resp.strip()
    # Markdownブロック除去
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl > 0:
            s = s[first_nl + 1 :]
        if s.endswith("```"):
            s = s[: -3]
        s = s.strip()
    # JSON行だけ抽出（前後に文があるケース）
    start = s.find("{")
    end = s.rfind("}")
    if start < 0 or end < 0:
        raise ValueError(f"JSON not found in response: {resp[:200]}")
    return json.loads(s[start : end + 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="先頭N件のみ処理")
    ap.add_argument("--resume", action="store_true", help="既存結果に追記")
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--sleep", type=float, default=6.0, help="API呼び出し間のsleep秒（rate limit対策）")
    args = ap.parse_args()

    cats = load_categories()
    kokuji_text = load_kokuji_raw()
    samples = load_sample_ingredients()
    claude_verdicts = load_claude_verdicts()

    results: dict = {}
    if args.resume and OUT.exists():
        results = json.loads(OUT.read_text(encoding="utf-8"))
        log(f"resume: 既存 {len(results)} 件を読込")

    targets = cats
    if args.limit is not None:
        targets = cats[: args.limit]

    processed = 0
    skipped = 0
    errors = 0

    for i, c in enumerate(targets):
        name = c["name"]
        if name in results and results[name].get("verdict"):
            skipped += 1
            continue

        condition = c.get("condition") or "なし"
        cv = claude_verdicts.get(name, "?")
        sample_ing = samples.get(name, [])
        prompt = PROMPT_TEMPLATE.format(
            category_name=name,
            condition=condition,
            sample_ingredients="、".join(sample_ing) if sample_ing else "該当品目なし",
            claude_verdict=cv,
            kokuji_excerpt=build_kokuji_excerpt(name, kokuji_text),
        )

        log(f"[{i+1}/{len(targets)}] {name}（Claude判定: {cv}）")
        try:
            raw = ask_gemini(prompt, model=args.model)
            parsed = parse_gemini_response(raw)
            parsed["claude_verdict"] = cv
            parsed["agrees"] = parsed.get("verdict") == cv
            parsed["raw_response"] = raw[:1500]  # truncated for storage
            results[name] = parsed
            log(f"  → Gemini: {parsed.get('verdict')} ({'一致' if parsed['agrees'] else '相違！'})")
            processed += 1
        except Exception as e:
            log(f"  ! ERROR: {e}")
            results[name] = {
                "error": str(e)[:300],
                "claude_verdict": cv,
            }
            errors += 1

        # Save progress after each call
        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

        # Rate limit対策
        if args.sleep > 0 and i < len(targets) - 1:
            time.sleep(args.sleep)

    log(f"\nサマリ: processed={processed}, skipped={skipped}, errors={errors}")
    # 相違点集計
    disagreements = [(n, v) for n, v in results.items() if v.get("verdict") and not v.get("agrees")]
    log(f"判定相違: {len(disagreements)}件")
    for n, v in disagreements[:20]:
        log(f"  [{n}] Claude: {v.get('claude_verdict')} vs Gemini: {v.get('verdict')}")

    log(f"\n出力: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
