"""Gemini検証データをマスタCSVに統合し、品目ごとに理由・処方方法・告示原文を付与。

Input:
  data/master.csv                      Claude判定結果
  data/gemini_verification.json        Gemini検証結果（カテゴリ別）

Output:
  data/master_enriched.csv             全フィールド + 理由/方法/原文
  app/data.json                        Web用圧縮JSON（拡張スキーマ）

スキーマ変更:
  app/data.json の各品目に追加フィールド:
    reason_why: なぜこの判定か（80-150字）
    method: △の場合の処方方法（100-250字）、○/×はnull
    source: 告示原文該当部分（30-200字）
    verified: bool - Gemini検証済みか
    agrees: bool - Claude判定とGemini判定が一致しているか
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "data/master.csv"
VERIF = ROOT / "data/gemini_verification.json"
OUT_ENRICHED = ROOT / "data/master_enriched.csv"
OUT_APPJSON = ROOT / "app/data.json"
OUT_META = ROOT / "app/meta.json"


def parse_categories_from_reason(reason: str) -> list[str]:
    """判定根拠テキストから [カテゴリ名] を抽出"""
    m = re.search(r"\[([^\]]+)\]", reason)
    if not m:
        return []
    return [c.strip() for c in m.group(1).split("/")]


def main() -> int:
    verif = {}
    if VERIF.exists():
        verif = json.loads(VERIF.read_text(encoding="utf-8"))

    rows = []
    with MASTER.open(encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        fieldnames = rdr.fieldnames or []
        for r in rdr:
            rows.append(r)

    # Enrichment
    verdict_stats = Counter()
    agree_stats = {"agree": 0, "disagree": 0, "unverified": 0}

    enriched = []
    for r in rows:
        cats = parse_categories_from_reason(r["判定根拠"])
        # Pick first category that has verification
        reason_why = ""
        method = ""
        source_text = ""
        verified = False
        agrees = None
        gemini_verdict = ""
        used_category = ""
        for cat in cats:
            v = verif.get(cat)
            if v and v.get("verdict"):
                reason_why = v.get("reason_why", "")
                method = v.get("prescription_method") or ""
                source_text = v.get("source_text", "")
                gemini_verdict = v.get("verdict", "")
                # agrees はこの品目の現在の判定と Gemini 判定の比較で再計算
                # （verification.json 内の agrees は検証時点の値で古い可能性がある）
                agrees = (gemini_verdict == r["院外処方可否"])
                used_category = cat
                verified = True
                break

        if verified:
            agree_stats["agree" if agrees else "disagree"] += 1
        else:
            agree_stats["unverified"] += 1
        verdict_stats[r["院外処方可否"]] += 1

        enriched.append({
            **r,
            "理由解説": reason_why,
            "処方方法": method,
            "告示原文": source_text,
            "Gemini判定": gemini_verdict,
            "検証済み": "yes" if verified else "no",
            "判定一致": "一致" if agrees is True else ("相違" if agrees is False else ""),
            "参照カテゴリ": used_category,
        })

    # Write enriched CSV
    OUT_ENRICHED.write_text(
        "",  # create
        encoding="utf-8",
    )
    with OUT_ENRICHED.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(enriched[0].keys()))
        w.writeheader()
        for r in enriched:
            w.writerow(r)
    print(f"→ {OUT_ENRICHED} ({len(enriched)}品目)")

    # Write compact JSON for app
    compact = []
    for r in enriched:
        compact.append({
            "n": r["販売名"],
            "s": r["成分名"],
            "k": r["規格"],
            "y": r["YJコード"],
            "m": r["メーカー"],
            "h": r["先発後発"],
            "p": r["薬価"],
            "g": r["院外処方可否"],  # ○/△/×/－
            "r": r["判定根拠"],        # 短縮根拠（従来）
            "d": r["廃止経過措置"] or "",
            "x": r["廃止区分"] or "",
            # NEW 拡張フィールド
            "why": r["理由解説"] or "",
            "how": r["処方方法"] or "",
            "src": r["告示原文"] or "",
            "ver": r["検証済み"] == "yes",
        })
    OUT_APPJSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_APPJSON.write_text(
        json.dumps(compact, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size = OUT_APPJSON.stat().st_size
    print(f"→ {OUT_APPJSON}  ({len(compact)}品目, {size/1024:.1f}KB)")

    # Meta update
    existing_meta = {}
    if OUT_META.exists():
        existing_meta = json.loads(OUT_META.read_text(encoding="utf-8"))
    meta = {
        **existing_meta,
        "stats": dict(verdict_stats),
        "total": len(compact),
        "verification": {
            "agree": agree_stats["agree"],
            "disagree": agree_stats["disagree"],
            "unverified": agree_stats["unverified"],
        },
        "caveat": "本ツールは機械突合＋Gemini検証の参考情報です。○は告示に具体記載、△は条件付き/薬効分類名包括記載、×は告示非該当。品目ごとの「なぜこの判定か」「条件付きでの処方方法」「告示原文」を詳細欄で参照できます。最終判定は必ず告示原文をご確認ください。",
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {OUT_META}")
    print(f"\n検証サマリ: 一致 {agree_stats['agree']} / 相違 {agree_stats['disagree']} / 未検証 {agree_stats['unverified']}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
