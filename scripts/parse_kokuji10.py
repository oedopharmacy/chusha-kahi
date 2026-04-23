"""
告示107号 第十 第一号 の本文テキストから、院外処方可能な注射薬カテゴリを
構造化JSONに変換する。

入力: data/kokuji_dai10_raw.txt
出力: data/kokuji_categories.json

各カテゴリは以下の形式:
{
  "name": "インスリン製剤",         # カテゴリ名（告示原文ママ）
  "name_normalized": "インスリン製剤",  # 検索用正規化（ルビ括弧除去等）
  "condition": null | "在宅血液透析患者に対して使用する場合に限る。" など
}
"""
import json
import re
from pathlib import Path

SRC = Path("data/kokuji_dai10_raw.txt")
OUT = Path("data/kokuji_categories.json")


def extract_daiichi_list(full_text: str) -> str:
    """第十 第一号 の本文部分（カテゴリの並んだ部分）を抽出"""
    # 第十 第一号 の見出し直後から第二号の直前まで
    m = re.search(r"一　療担規則第二十条第二号ト.*?及びパロペグテリパラチド製剤", full_text, re.S)
    if m:
        body = m.group(0)
        # 見出し行を除去
        body = re.sub(r"^一　療担規則第二十条第二号ト[^\n]*\n", "", body)
        return body
    # フォールバック: 第一号ヘッダ以降を第二号まで
    m = re.search(r"第十　厚生労働大臣が定める注射薬等\s*一　[^\n]*\n(.*?)二　投薬期間に上限", full_text, re.S)
    if not m:
        raise SystemExit("第十 第一号 の本文を特定できません")
    return m.group(1).strip()


def split_categories(body: str) -> list[str]:
    """カテゴリを「、」で分割。括弧内の「、」は保護する。"""
    items = []
    depth = 0
    cur = []
    for ch in body:
        if ch in "（(":
            depth += 1
            cur.append(ch)
        elif ch in "）)":
            depth -= 1
            cur.append(ch)
        elif ch == "、" and depth == 0:
            s = "".join(cur).strip()
            if s:
                items.append(s)
            cur = []
        else:
            cur.append(ch)
    # 末尾
    tail = "".join(cur).strip()
    if tail:
        items.append(tail)
    # 最後の要素は「及び〜」で区切られていることがある
    last = items[-1]
    # "A及びB" を [A, B] に
    if "及び" in last:
        a, b = last.rsplit("及び", 1)
        items = items[:-1] + [a.strip(), b.strip()]
    return [x for x in items if x]


def parse_category(raw: str) -> dict:
    """カテゴリ文字列を name / condition に分解"""
    # ルビ括弧を剥がす（「灌かん流」→「灌流」、「迂う回」→「迂回」など）
    # 告示の慣用表記でひらがな1文字が漢字の直後に挿入される。安全策として
    # 「漢字 + ひらがな1字」で前の漢字と同じ読みのものは後で正規化に回す。
    # まず条件句（括弧内）を抽出
    # 日本語の括弧「（」「）」と半角「(」「)」両方に対応
    m = re.search(r"[（(](.*)[）)]\s*$", raw)
    name = raw
    condition = None
    if m:
        condition = m.group(1).strip()
        name = raw[: m.start()].strip()
    return {
        "name": name,
        "name_normalized": normalize_name(name),
        "condition": condition,
    }


_RUBY_RE = re.compile(r"([一-龠])([ぁ-ん])(?=[一-龠])")


def normalize_name(name: str) -> str:
    """ルビひらがな挿入を除去してマッチしやすくする"""
    # 「灌かん流」→「灌流」、「迂う回」→「迂回」
    # ただし「サト(ラ)リズマブ」のような外来語は対象外
    # 単純ルール: 漢字 + ひらがな1字 + 漢字 の並びで、真ん中のひらがなを削除
    prev = None
    out = name
    while prev != out:
        prev = out
        out = _RUBY_RE.sub(r"\1", out)
    # 全角→半角の「・」「－」正規化はここでは行わない（告示原文を尊重）
    return out


def main():
    text = SRC.read_text(encoding="utf-8")
    body = extract_daiichi_list(text)
    items = split_categories(body)
    cats = [parse_category(s) for s in items]

    OUT.write_text(json.dumps(cats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Parsed {len(cats)} categories → {OUT}")
    print("\nFirst 10:")
    for c in cats[:10]:
        print(" ", c)
    print("\nWith conditions:")
    for c in cats:
        if c["condition"]:
            print(" ", c["name"], "::", c["condition"][:60])


if __name__ == "__main__":
    main()
