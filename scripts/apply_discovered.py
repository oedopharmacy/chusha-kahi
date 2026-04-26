"""discovered_aliases.json から両AI一致のものを category_aliases.yaml に追加。

両AIが同じ告示カテゴリを示した成分のみ採用（ハルシネーション抑止）。
"""
from __future__ import annotations

import csv
import json
import yaml
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DISC = ROOT / "data/discovered_aliases.json"
ALIASES = ROOT / "data/category_aliases.yaml"
YAKKA = ROOT / "data/yakka_chusha_raw.csv"


def main() -> int:
    if not DISC.exists():
        print("discovered_aliases.json なし")
        return 1
    disc = json.loads(DISC.read_text(encoding="utf-8"))
    actual = set(r["成分名"] for r in csv.DictReader(YAKKA.open(encoding="utf-8")))

    # 両AIが同じカテゴリを示した成分のみ
    by_cat = defaultdict(list)
    for seibun, opinions in disc.items():
        gem = (opinions.get("gemini") or {}).get("category")
        gpt = (opinions.get("gpt") or {}).get("category")
        if gem and gpt and gem == gpt and seibun in actual:
            by_cat[gem].append(seibun)

    print(f"両AI一致 alias 候補: {sum(len(v) for v in by_cat.values())} 成分 / {len(by_cat)} カテゴリ\n")
    for cat, seibuns in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        print(f"[{cat}] {len(seibuns)}成分")
        for s in seibuns[:3]:
            print(f"  ・{s}")
        if len(seibuns) > 3:
            print(f"  ... 他{len(seibuns) - 3}")

    # YAML 適用
    existing = yaml.safe_load(ALIASES.read_text(encoding="utf-8")) or {}
    added = 0
    for cat, seibuns in by_cat.items():
        cur = existing.get(cat) or []
        new = [s for s in seibuns if s not in cur]
        if new:
            existing[cat] = list(dict.fromkeys((cur or []) + new))
            added += len(new)
    ALIASES.write_text(
        yaml.safe_dump(existing, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    print(f"\n→ {ALIASES} に {added} 成分追加")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
