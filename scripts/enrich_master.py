"""Claude/Gemini/GPT 3者の判定 consensus をマスタCSVに統合。

Input:
  data/master.csv                      Claude判定結果
  data/consensus.json                  Claude/Gemini/GPT 3者比較
  (fallback: data/gemini_verification.json のみ)

Output:
  data/master_enriched.csv             全フィールド + 理由/方法/原文 + 3AI意見
  app/data.json                        Web用圧縮JSON（拡張スキーマ）

スキーマ変更:
  app/data.json の各品目に追加フィールド:
    why_g: Gemini の理由
    why_p: GPT の理由
    how_g: Gemini の処方方法（△の場合）
    how_p: GPT の処方方法
    src: 告示原文該当部分
    conf: confidence (high/medium/low/unknown)
    cv: { c, g, p } 3者 verdict
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
CONSENSUS = ROOT / "data/consensus.json"
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
    # consensus.json があれば優先、なければ gemini単独 を後方互換で使う
    consensus = {}
    if CONSENSUS.exists():
        consensus = json.loads(CONSENSUS.read_text(encoding="utf-8"))
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
        reason_why_g = reason_why_p = ""
        method_g = method_p = ""
        source_text = ""
        verified = False
        agrees = None
        gemini_verdict = ""
        gpt_verdict = ""
        consensus_verdict = ""
        confidence = ""
        used_category = ""
        for cat in cats:
            cn = consensus.get(cat)
            v = verif.get(cat)
            if cn and cn.get("consensus_verdict"):
                reason_why_g = cn.get("reason_why_gemini", "") or (v.get("reason_why", "") if v else "")
                reason_why_p = cn.get("reason_why_gpt", "")
                method_g = cn.get("method_gemini", "") or (v.get("prescription_method") or "" if v else "")
                method_p = cn.get("method_gpt", "")
                source_text = cn.get("source_text", "") or (v.get("source_text", "") if v else "")
                gemini_verdict = cn["verdicts"].get("gemini", "") or ""
                gpt_verdict = cn["verdicts"].get("gpt", "") or ""
                consensus_verdict = cn.get("consensus_verdict", "")
                confidence = cn.get("confidence", "")
                used_category = cat
                verified = True
                # この品目の現在の判定と consensus を比較
                agrees = (consensus_verdict == r["院外処方可否"])
                break
            elif v and v.get("verdict"):
                reason_why_g = v.get("reason_why", "")
                method_g = v.get("prescription_method") or ""
                source_text = v.get("source_text", "")
                gemini_verdict = v.get("verdict", "")
                used_category = cat
                verified = True
                agrees = (gemini_verdict == r["院外処方可否"])
                break

        if verified:
            agree_stats["agree" if agrees else "disagree"] += 1
        else:
            agree_stats["unverified"] += 1
        verdict_stats[r["院外処方可否"]] += 1

        enriched.append({
            **r,
            "理由_Gemini": reason_why_g,
            "理由_GPT": reason_why_p,
            "処方方法_Gemini": method_g,
            "処方方法_GPT": method_p,
            "告示原文": source_text,
            "Gemini判定": gemini_verdict,
            "GPT判定": gpt_verdict,
            "consensus判定": consensus_verdict,
            "confidence": confidence,
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
            "g": r["院外処方可否"],  # ○/△/×/－（Claude判定 = master.csv上の最終）
            "r": r["判定根拠"],
            "d": r["廃止経過措置"] or "",
            "x": r["廃止区分"] or "",
            # 3AI 検証
            "why_g": r["理由_Gemini"] or "",
            "why_p": r["理由_GPT"] or "",
            "how_g": r["処方方法_Gemini"] or "",
            "how_p": r["処方方法_GPT"] or "",
            "src": r["告示原文"] or "",
            "cv": {"c": r["院外処方可否"], "g": r["Gemini判定"], "p": r["GPT判定"]},
            "conf": r["confidence"] or "",
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
