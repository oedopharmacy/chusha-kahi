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
    # meta.json を更新。既存の source_yakka_url, last_updated, source_yakka は
    # update_data.py が最新値に書き換えるため、ここでは未指定時のみデフォルトを入れる。
    existing = {}
    if OUT_META.exists():
        try:
            existing = json.loads(OUT_META.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    meta = {
        "source_yakka": existing.get("source_yakka", "令和8年4月15日適用 薬価基準収載品目リスト（注射薬）"),
        "source_yakka_url": existing.get("source_yakka_url", ""),
        "source_kokuji": "平成18年厚労省告示第107号 第十 第一号（令和8年2月1日適用版）",
        "total": len(rows),
        "stats": dict(stats),
        "last_updated": existing.get("last_updated", ""),
        "caveat": "本ツールは機械突合による参考情報です。○は告示に具体的カテゴリ/成分名で記載、△は告示の条件付き記載または薬効分類名包括記載のため個別確認が必要、×は告示非該当を意味します。最終判定は必ず告示原文・関連通知をご確認ください。",
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {OUT_META}")


if __name__ == "__main__":
    main()
