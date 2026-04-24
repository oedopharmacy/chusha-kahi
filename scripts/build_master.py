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
RULES = ROOT / "data/category_rules.yaml"
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

def build_component_category_map(cats, aliases, rules):
    """成分名 + YJコード → [該当カテゴリ] のマップを構築

    マッチ優先度:
      1. aliases YAML（明示的な成分→カテゴリ定義）
      2. category_rules.yaml の ingredients（薬効分類型カテゴリの明示成分リスト）
      3. カテゴリ名語幹の substring マッチ
      4. category_rules.yaml の yj4_codes（YJコード先頭4桁一致）
    """
    cat_by_name = {c["name"]: c for c in cats}

    def _match(seibun, yj_code):
        matches = []
        seibun_n = norm(seibun)
        yj4 = (yj_code or "")[:4]

        # 1. aliases 明示
        for cat_name, alias_list in aliases.items():
            if not alias_list:
                continue
            for a in alias_list:
                if norm(a) == seibun_n:
                    matches.append({"category": cat_name, "rule": "alias", "stem": norm(a)})
                    break

        # 2. category_rules.yaml の ingredients（明示成分リスト）
        for cat_name, rule in rules.items():
            if not cat_name:
                continue
            ingredients = (rule or {}).get("ingredients") or []
            for ing in ingredients:
                ing_n = norm(ing)
                if ing_n and (ing_n == seibun_n or ing_n in seibun_n):
                    matches.append({"category": cat_name, "rule": "ingredient_list", "stem": ing_n})
                    break

        matched_cat_names = {m["category"] for m in matches}

        # 3. 自動語幹マッチ
        for c in cats:
            if c["name"] in matched_cat_names:
                continue
            stem = c["stem_norm"]
            if not stem or len(stem) < 3:
                continue
            if stem in seibun_n:
                matches.append({"category": c["name"], "rule": "substring", "stem": stem})
                matched_cat_names.add(c["name"])

        # 4. YJコード薬効分類マッチ（category_rules.yaml）
        if yj4 and yj4.isdigit():
            for cat_name, rule in rules.items():
                if cat_name in matched_cat_names:
                    continue
                yj4_list = (rule or {}).get("yj4_codes") or []
                if yj4 in [str(x) for x in yj4_list]:
                    matches.append({"category": cat_name, "rule": f"yj4:{yj4}", "stem": yj4})
                    matched_cat_names.add(cat_name)

        # 重複排除: 他マッチの語幹に内包される短い語幹マッチは除外
        # （YJ4とalias/ingredientは stem が別ドメインなので比較対象外）
        text_matches = [m for m in matches if not m["rule"].startswith("yj4")]
        code_matches = [m for m in matches if m["rule"].startswith("yj4")]
        filtered_text = []
        for m in text_matches:
            s = m["stem"]
            is_subsumed = False
            for m2 in text_matches:
                if m is m2:
                    continue
                if s != m2["stem"] and s in m2["stem"]:
                    is_subsumed = True
                    break
            if not is_subsumed:
                filtered_text.append(m)
        return filtered_text + code_matches
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


def load_rules():
    if not RULES.exists():
        return {}
    data = yaml.safe_load(RULES.read_text(encoding="utf-8")) or {}
    return data


# ---------------- メイン ----------------

def main():
    cats = load_cats()
    aliases = load_aliases()
    rules = load_rules()
    matcher = build_component_category_map(cats, aliases, rules)

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

        # カテゴリマッチ（成分名 + YJコード）
        cache_key = (seibun, (yj_code or "")[:4])
        if cache_key not in sei_cache:
            sei_cache[cache_key] = matcher(seibun, yj_code)
        matches = sei_cache[cache_key]

        # 院外可否判定（4段階：○／△／×／－）
        #
        # ○  告示の具体的カテゴリ/成分/製剤名にマッチ（alias/substring/ingredient_list）
        #     かつ 告示に条件記載なし
        # △  告示の薬効分類名にYJコードのみでマッチ（broad classification）
        #     OR 告示に条件記載あり（在宅血液透析限定、ALS限定等）
        # ×  告示第十第一号のどのカテゴリにも該当せず
        # －  告示別表2 削除品目
        if is_delisted:
            gaika = "－"
            gaika_reason = "保険使用不可（告示別表2に収載＝削除品目）"
            stats["削除"] += 1
        elif matches:
            # 各マッチを「具体的」「条件付」「YJ4のみ」に分類
            cat_info = {c["name"]: c for c in cats}
            specific_no_cond = []   # alias/substring/ingredient_list かつ 条件なし → ○ 候補
            specific_with_cond = [] # 具体マッチだが告示に条件付き記載
            yj4_only = []           # YJ4 マッチのみ
            for m in matches:
                is_yj4 = m["rule"].startswith("yj4")
                cat = cat_info.get(m["category"])
                has_cond = bool(cat and cat.get("condition"))
                if is_yj4:
                    yj4_only.append(m)
                elif has_cond:
                    specific_with_cond.append((m, cat.get("condition")))
                else:
                    specific_no_cond.append(m)

            if specific_no_cond:
                # 告示に具体的カテゴリ名で無条件記載 → ○（優先）
                gaika = "○"
                cats_str = "/".join(m["category"] for m in specific_no_cond)
                rules_str = ",".join(m["rule"] for m in specific_no_cond)
                gaika_reason = f"告示第十第一号 [{cats_str}] に該当（{rules_str}）"
                stats["○"] += 1
            elif specific_with_cond:
                # 具体マッチは条件付きのみ → △（条件を verbatim 表示）
                gaika = "△"
                cond_str = " / ".join(f"[{m['category']}]:{c}" for m, c in specific_with_cond)
                cats_str = "/".join(m["category"] for m, _ in specific_with_cond)
                gaika_reason = (
                    f"告示第十第一号 [{cats_str}] "
                    f"該当（要確認: 告示に条件記載あり）{cond_str}"
                )
                stats["△"] = stats.get("△", 0) + 1
            elif yj4_only:
                # YJ薬効分類コードのみでマッチ → △（包括分類名記載のため個別確認必要）
                gaika = "△"
                cats_str = "/".join(m["category"] for m in yj4_only)
                codes = ",".join(m["stem"] for m in yj4_only)
                gaika_reason = (
                    f"告示第十第一号 [{cats_str}] "
                    f"に薬効分類名で包括記載（YJコード{codes}で該当）"
                    f"※個別品目の臨床適合性・管理料要件を別途確認"
                )
                stats["△"] = stats.get("△", 0) + 1
            else:
                gaika = "○"
                cats_str = "/".join(m["category"] for m in matches)
                gaika_reason = f"告示第十第一号 [{cats_str}] に該当"
                stats["○"] += 1
        else:
            gaika = "×"
            gaika_reason = "告示第十第一号のどのカテゴリにも該当せず（院外処方箋での交付不可が原則）"
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
