"""Gemini検証データから Claude vs Gemini 判定の相違点をレビューしやすく整形。

Output:
  data/disagreements.md          人間レビュー用Markdown
  標準出力                        サマリ集計
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIF = ROOT / "data/gemini_verification.json"
OUT_MD = ROOT / "data/disagreements.md"


def main() -> int:
    if not VERIF.exists():
        print("Run gemini_verify.py first")
        return 1
    v = json.loads(VERIF.read_text(encoding="utf-8"))

    agree = []
    disagree = []
    errors = []
    for name, item in v.items():
        if "error" in item:
            errors.append((name, item["error"]))
        elif item.get("agrees"):
            agree.append(name)
        elif item.get("verdict"):
            disagree.append((name, item))

    total = len(v)
    print(f"=== Gemini検証サマリ ===")
    print(f"  検証カテゴリ: {total}")
    print(f"  一致: {len(agree)}")
    print(f"  相違: {len(disagree)}")
    print(f"  エラー: {len(errors)}")
    print()

    # 相違パターン集計
    pattern = Counter()
    for name, item in disagree:
        pattern[(item.get("claude_verdict"), item.get("verdict"))] += 1
    print("相違パターン:")
    for (claude, gemini), c in pattern.most_common():
        print(f"  Claude {claude} → Gemini {gemini}: {c}件")
    print()

    # Markdown出力
    lines = ["# Claude vs Gemini 判定相違レビュー\n"]
    lines.append(f"検証: {total}カテゴリ / 一致 {len(agree)} / 相違 {len(disagree)} / エラー {len(errors)}\n")
    lines.append("## 相違一覧\n")
    for name, item in disagree:
        lines.append(f"### {name}")
        lines.append(f"- **Claude判定**: `{item.get('claude_verdict')}`")
        lines.append(f"- **Gemini判定**: `{item.get('verdict')}`")
        lines.append(f"- **Geminiの理由**: {item.get('reason_why', '')}")
        if item.get("prescription_method"):
            lines.append(f"- **処方方法**: {item.get('prescription_method')}")
        lines.append(f"- **告示原文**: \n  > {item.get('source_text', '').replace(chr(10), chr(10) + '  > ')}")
        lines.append("")

    if errors:
        lines.append("## エラー\n")
        for name, err in errors:
            lines.append(f"- **{name}**: {err}")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"→ {OUT_MD}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
