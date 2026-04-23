"""
薬価基準の注射薬成分名(928種) × 告示第十第一号カテゴリ(136件) を突合する
1次ドラフト生成スクリプト。

出力:
  data/match_draft.csv  成分ごとに、該当カテゴリ候補を列挙。人手レビュー用。
  data/match_stats.txt  集計

方針:
  A) カテゴリ名から「語幹」を抽出（例: "インスリン製剤" → ["インスリン"]）
     - 「○○製剤」「○○剤」「○○配合剤」等の接尾辞を剥離
     - 主要な接頭辞（「遺伝子組換え」「乾燥人」「pH4処理」等）は剥がさず残す
  B) 成分名に語幹が含まれるか判定（正規化: 全角ルビ除去、スペース統一）
  C) マッチ結果を rule 付きで記録

重要: 本マッチは1次ドラフト。最終判定は薬剤師レビュー前提。
"""
import csv
import json
import re
from collections import defaultdict, Counter
from pathlib import Path

YAKKA_CSV = Path("data/yakka_chusha_raw.csv")
CATS_JSON = Path("data/kokuji_categories.json")
OUT_DRAFT = Path("data/match_draft.csv")
OUT_STATS = Path("data/match_stats.txt")


# ---------------- 正規化 ----------------

_RUBY_RE = re.compile(r"([一-龠])([ぁ-ん])(?=[一-龠])")
_SPACE_RE = re.compile(r"[\s　]+")


def norm(s: str) -> str:
    """成分名・カテゴリ名を比較用に正規化"""
    if s is None:
        return ""
    s = str(s)
    # ルビひらがな（「迂う回」「灌かん流」等）除去
    prev = None
    while prev != s:
        prev = s
        s = _RUBY_RE.sub(r"\1", s)
    # 全角スペース・半角スペース・中黒の扱い
    s = s.replace("・", "")  # 中黒は比較時に無視
    s = _SPACE_RE.sub("", s)
    # ローマ数字の全角/半角統一は難しいので原文ママ
    return s


# ---------------- 語幹抽出 ----------------

# カテゴリ名から剥がす接尾辞（長いものから試行）
_SUFFIX_PATTERNS = [
    "配合剤",
    "製剤",
    "剤",
]


def extract_stem(cat_name: str) -> str:
    """カテゴリ名から語幹を抽出
    例: "インスリン製剤" -> "インスリン"
        "乾燥人血液凝固第Ⅷ因子製剤" -> "乾燥人血液凝固第Ⅷ因子"
        "インスリン・グルカゴン様ペプチド―1受容体アゴニスト配合剤" -> "インスリングルカゴン様ペプチド―1受容体アゴニスト"
    """
    s = norm(cat_name)
    for suf in _SUFFIX_PATTERNS:
        if s.endswith(suf) and len(s) > len(suf) + 1:
            return s[: -len(suf)]
    return s


# ---------------- マッチング ----------------


def main():
    # カテゴリ読み込み
    cats = json.loads(CATS_JSON.read_text(encoding="utf-8"))
    for c in cats:
        c["stem"] = extract_stem(c["name"])
        c["stem_norm"] = norm(c["stem"])

    # 成分名を薬価基準から集める（ユニーク）
    seibun_rows = defaultdict(list)  # seibun_raw -> [yakka rows]
    with YAKKA_CSV.open(encoding="utf-8") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        for r in rdr:
            seibun = r[2]
            seibun_rows[seibun].append(r)
    print(f"成分名ユニーク: {len(seibun_rows)}")

    # マッチング: 成分名 に カテゴリ語幹 が含まれるか
    draft = []  # rows for CSV output
    stats = {"AUTO_OK": 0, "MULTI": 0, "UNMATCHED": 0}

    for seibun, rows in sorted(seibun_rows.items()):
        sn = norm(seibun)
        matches = []
        for c in cats:
            stem = c["stem_norm"]
            if not stem:
                continue
            # 完全一致 or サブストリング
            rule = None
            if sn == stem:
                rule = "exact"
            elif stem in sn:
                rule = "substring"
            elif sn in stem and len(sn) >= 3:
                # 逆向き: 成分名がカテゴリ語幹の一部（例: 成分「ダルベポエチン」⊂ カテゴリ語幹「ダルベポエチン」はない…）
                # 通常成分は長いので rare
                rule = "reverse_substring"
            if rule:
                matches.append({
                    "category": c["name"],
                    "stem": c["stem"],
                    "rule": rule,
                    "condition": c.get("condition"),
                })

        if not matches:
            status = "UNMATCHED"
        elif len(matches) == 1:
            status = "AUTO_OK"
        else:
            status = "MULTI"
        stats[status] += 1

        # 代表行は成分あたり1行だが、販売名ごとに最終マスタへ展開される
        hanbai_count = len(rows)
        keika_count = sum(1 for r in rows if r[13])  # 経過措置
        match_str = "; ".join(
            f"{m['category']}[{m['rule']}]" + (f"(条件:{m['condition'][:30]})" if m["condition"] else "")
            for m in matches
        )
        draft.append({
            "成分名": seibun,
            "成分名正規化": sn,
            "販売名数": hanbai_count,
            "うち経過措置": keika_count,
            "マッチ状態": status,
            "マッチしたカテゴリ": match_str,
            "マッチ件数": len(matches),
        })

    # CSV 出力
    with OUT_DRAFT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(draft[0].keys()))
        w.writeheader()
        for row in draft:
            w.writerow(row)
    print(f"→ {OUT_DRAFT}")

    # 統計出力
    with OUT_STATS.open("w", encoding="utf-8") as f:
        f.write(f"成分名ユニーク数: {len(seibun_rows)}\n")
        f.write(f"  AUTO_OK (1カテゴリのみマッチ): {stats['AUTO_OK']}\n")
        f.write(f"  MULTI (複数カテゴリにマッチ→要精査): {stats['MULTI']}\n")
        f.write(f"  UNMATCHED (どのカテゴリにもマッチせず): {stats['UNMATCHED']}\n")
    print(OUT_STATS.read_text(encoding="utf-8"))

    # カテゴリ別にマッチ件数を表示
    cat_hits = Counter()
    for d in draft:
        if d["マッチ状態"] in ("AUTO_OK", "MULTI"):
            for frag in d["マッチしたカテゴリ"].split("; "):
                cat = frag.split("[")[0]
                cat_hits[cat] += 1
    print("\nカテゴリ別ヒット数 Top 20:")
    for cat, n in cat_hits.most_common(20):
        print(f"  {n:4d}  {cat}")
    print("\nヒット0のカテゴリ:")
    hit_names = set(cat_hits.keys())
    for c in cats:
        if c["name"] not in hit_names:
            print(f"  ✗ {c['name']}")


if __name__ == "__main__":
    main()
