"""
マスタCSV生成スクリプト（販売名レベル）

入力:
  data/yakka_chusha_raw.csv     薬価基準（注射薬）
  data/kokuji_categories.json    告示第十第一号カテゴリ
  data/category_aliases.yaml     成分名→カテゴリ alias（人手保守）
  raw/kokuji/kokuji107_p2.html   告示別表1,2（削除品目）

出力:
  data/master.csv     販売名ごとに全情報 + 院外処方可否
  data/review.csv     要レビュー品目（AUTO_OK成分、UNMATCHED成分、MULTIマッチ、etc.）

判定ロジック:
  1. 品名が告示別表1/別表2に載っている → 保険使用不可（削除済）、院外可否は "－"
  2. それ以外で、成分名が aliases または 自動マッチで告示第十第一号カテゴリに該当
     → 院外可否 = ○
  3. 上記に該当せず → 院外可否 = ×（院内のみ）
  4. 経過措置期限が設定されている → 廃止予定フラグ ON
"""
import csv
import json
import re
import html as htmllib
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(".")
YAKKA = ROOT / "data/yakka_chusha_raw.csv"
CATS = ROOT / "data/kokuji_categories.json"
ALIASES = ROOT / "data/category_aliases.yaml"
KOKUJI_P2 = ROOT / "raw/kokuji/kokuji107_p2.html"
OUT_MASTER = ROOT / "data/master.csv"
OUT_REVIEW = ROOT / "data/review.csv"
OUT_DELIST = ROOT / "data/delisted_injection.csv"


# ---------------- 正規化 ----------------
_RUBY_RE = re.compile(r"([一-龠])([ぁ-ん])(?=[一-龠])")
_SPACE_RE = re.compile(r"[\s　]+")


def norm(s) -> str:
    if s is None:
        return ""
    s = str(s)
    prev = None
    while prev != s:
        prev = s
        s = _RUBY_RE.sub(r"\1", s)
    s = s.replace("・", "")
    s = _SPACE_RE.sub("", s)
    return s


_SUFFIX = ["配合剤", "製剤", "剤"]


def extract_stem(cat_name: str) -> str:
    s = norm(cat_name)
    for suf in _SUFFIX:
        if s.endswith(suf) and len(s) > len(suf) + 1:
            return s[: -len(suf)]
    return s


# ---------------- 削除品目リスト取得 ----------------

def extract_delisted_injections() -> set:
    """告示別表1・別表2 の 第2部 注射薬 セクションから品名を抽出

    HTMLのテーブル構造（<tr><td>品名</td><td>規格単位</td></tr>）をそのままパースする。
    """
    with KOKUJI_P2.open("rb") as f:
        h = f.read().decode("utf-8", errors="replace")
    # 第2部 注射薬 以下 第3部 までの HTML ブロックを抽出（2回出現）
    results = set()
    for m in re.finditer(r"第2部[^<]*注射薬(.*?)第3部", h, flags=re.S):
        block = m.group(1)
        # 各セル (<td>...</td>) を順番に取る
        cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", block)
        # 先頭セルが「品名」と「規格単位」のヘッダなので、それ以降を2つずつペア
        clean_cells = []
        for c in cells:
            t = re.sub(r"<[^>]+>", "", c)
            t = htmllib.unescape(t)
            t = t.strip()
            # ふりがな見出し (あ)(い)など、または空セルは無視
            if not t or re.match(r"^\([ぁ-ん一-龠]\)$", t) or t in ("品名", "規格単位"):
                continue
            clean_cells.append(t)
        # 2つずつ (name, kikaku) ペア
        for i in range(0, len(clean_cells) - 1, 2):
            name = clean_cells[i]
            name = re.sub(r"^\(\(局\)\)\s*", "", name).strip()
            # ルビ除去
            name_norm = _RUBY_RE.sub(r"\1", name)
            prev = None
            while prev != name_norm:
                prev = name_norm
                name_norm = _RUBY_RE.sub(r"\1", name_norm)
            if name_norm:
                results.add(name_norm)
    return results


# ---------------- マッチング ----------------

def build_component_category_map(cats, aliases):
    """成分名 → [該当カテゴリ] のマップを構築
    ・aliases YAMLに明記されていれば確定
    ・成分名にカテゴリ語幹が含まれれば候補
    """
    def _match(seibun):
        matches = []
        seibun_n = norm(seibun)
        # 1. alias 明示
        for cat_name, alias_list in aliases.items():
            if not alias_list:
                continue
            for a in alias_list:
                if norm(a) == seibun_n:
                    matches.append({"category": cat_name, "rule": "alias", "stem": norm(a)})
                    break
        matched_cat_names = {m["category"] for m in matches}
        # 2. 自動語幹マッチ
        for c in cats:
            if c["name"] in matched_cat_names:
                continue
            stem = c["stem_norm"]
            if not stem or len(stem) < 3:
                continue
            if stem in seibun_n:
                matches.append({"category": c["name"], "rule": "substring", "stem": stem})
        # 3. 重複排除: 他マッチの語幹に内包される短い語幹マッチは除外
        #    例: 成分「アポモルヒネ塩酸塩水和物」で「モルヒネ塩酸塩」と「アポモルヒネ塩酸塩」両方マッチ
        #        → 後者（長い方）のみ残す
        filtered = []
        for m in matches:
            s = m["stem"]
            is_subsumed = False
            for m2 in matches:
                if m is m2:
                    continue
                if s != m2["stem"] and s in m2["stem"]:
                    is_subsumed = True
                    break
            if not is_subsumed:
                filtered.append(m)
        return filtered
    return _match


def load_cats():
    cats = json.loads(CATS.read_text(encoding="utf-8"))
    for c in cats:
        c["stem_norm"] = norm(extract_stem(c["name"]))
    return cats


def load_aliases():
    data = yaml.safe_load(ALIASES.read_text(encoding="utf-8")) or {}
    # None を [] に正規化
    return {k: (v or []) for k, v in data.items()}


# ---------------- メイン ----------------

def main():
    cats = load_cats()
    aliases = load_aliases()
    matcher = build_component_category_map(cats, aliases)

    # 削除品目リスト
    delisted = extract_delisted_injections()
    print(f"告示別表の削除注射薬: {len(delisted)}")
    OUT_DELIST.write_text(
        "\n".join(sorted(delisted)), encoding="utf-8"
    )

    # 薬価基準を読み込み、品目ごとに判定
    rows = []
    with YAKKA.open(encoding="utf-8") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        rows = list(rdr)
    print(f"薬価基準注射薬: {len(rows)}品目")

    master_rows = []
    review_rows = []
    stats = {"○": 0, "×": 0, "削除": 0, "廃止予定": 0}

    # 成分ごとのマッチ結果をキャッシュ
    sei_cache = {}

    for r in rows:
        kubun, yj_code, seibun, kikaku = r[0], r[1], r[2], r[3]
        kyokuhou = r[4]
        hinmei = r[7]
        maker = r[8]
        senpatsu = r[10]
        yakka = r[12]
        keika = r[13]
        bikou = r[14]

        # 削除判定
        is_delisted = hinmei in delisted

        # カテゴリマッチ
        if seibun not in sei_cache:
            sei_cache[seibun] = matcher(seibun)
        matches = sei_cache[seibun]

        # 院外可否
        if is_delisted:
            gaika = "－"
            gaika_reason = "保険使用不可（告示別表2に収載＝削除品目）"
            stats["削除"] += 1
        elif matches:
            gaika = "○"
            cat_list = [m["category"] for m in matches]
            rules = [m["rule"] for m in matches]
            # 条件付きカテゴリか確認
            conds = []
            for m in matches:
                for c in cats:
                    if c["name"] == m["category"] and c.get("condition"):
                        conds.append(c["condition"])
            if conds:
                gaika_reason = (
                    f"告示第十第一号 [{'/'.join(cat_list)}] "
                    f"マッチ規則:{','.join(rules)} "
                    f"※条件付:{conds[0]}"
                )
            else:
                gaika_reason = f"告示第十第一号 [{'/'.join(cat_list)}] マッチ規則:{','.join(rules)}"
            stats["○"] += 1
        else:
            gaika = "×"
            gaika_reason = "告示第十第一号のどのカテゴリにも該当せず（院内処方のみ）"
            stats["×"] += 1

        haishi = "経過措置" if keika else ""
        if keika:
            stats["廃止予定"] += 1

        master_rows.append({
            "販売名": hinmei,
            "成分名": seibun,
            "規格": kikaku,
            "YJコード": yj_code,
            "メーカー": maker,
            "先発後発": senpatsu or "",
            "局方": kyokuhou or "",
            "薬価": yakka,
            "院外処方可否": gaika,
            "判定根拠": gaika_reason,
            "廃止経過措置": keika or "",
            "廃止区分": haishi,
            "備考": bikou or "",
        })

        # レビュー対象
        review_reason = []
        if matches and any(m["rule"] == "substring" for m in matches):
            review_reason.append("自動substring一致（要確認）")
        if len(matches) >= 2:
            review_reason.append("複数カテゴリマッチ")
        if is_delisted:
            review_reason.append("削除品目")
        if not matches and not is_delisted:
            # 成分名から院外可能性が疑われるものだけ review 対象にすると人手が楽だが、
            # まずは全UNMATCHEDを1回レビュー対象として出す
            review_reason.append("UNMATCHED（×判定の妥当性確認）")
        if review_reason:
            review_rows.append({
                "販売名": hinmei,
                "成分名": seibun,
                "規格": kikaku,
                "判定": gaika,
                "判定根拠": gaika_reason,
                "レビュー理由": "/".join(review_reason),
            })

    # 出力
    with OUT_MASTER.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(master_rows[0].keys()))
        w.writeheader()
        for r in master_rows:
            w.writerow(r)
    with OUT_REVIEW.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(review_rows[0].keys()))
        w.writeheader()
        for r in review_rows:
            w.writerow(r)

    print(f"\n判定サマリ:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\n→ {OUT_MASTER}")
    print(f"→ {OUT_REVIEW} ({len(review_rows)}件)")
    print(f"→ {OUT_DELIST}")


if __name__ == "__main__":
    main()
