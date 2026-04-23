"""master.csv を検索アプリ用のコンパクトJSON化する"""
import csv
import json
from pathlib import Path

MASTER = Path("data/master.csv")
OUT = Path("app/data.json")
OUT_META = Path("app/meta.json")


def main():
    rows = []
    with MASTER.open(encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append({
                "n": r["販売名"],
                "s": r["成分名"],
                "k": r["規格"],
                "y": r["YJコード"],
                "m": r["メーカー"],
                "h": r["先発後発"],
                "p": r["薬価"],
                "g": r["院外処方可否"],  # ○/×/－
                "r": r["判定根拠"],
                "d": r["廃止経過措置"] or "",
                "x": r["廃止区分"] or "",
            })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size = OUT.stat().st_size
    print(f"→ {OUT}  ({len(rows)}品目, {size/1024:.1f}KB)")

    from collections import Counter
    stats = Counter(r["g"] for r in rows)
    meta = {
        "source_yakka": "令和8年4月15日適用 薬価基準収載品目リスト（注射薬）",
        "source_kokuji": "平成18年厚労省告示第107号 第十（令和8年2月1日適用版）",
        "total": len(rows),
        "stats": dict(stats),
        "caveat": "本ツールは告示第十第一号のカテゴリ×成分名自動マッチに基づく参考情報です。最終判定は薬剤師・医師の判断で行ってください。"
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {OUT_META}")


if __name__ == "__main__":
    main()
