"""厚労省の薬価基準収載品目リスト（注射薬）を自動取得し、マスタを再構築する。

手順:
  1. 厚労省「医療保険が適用される医薬品について」ページから最新の詳細ページURLを取得
  2. 詳細ページから「注射薬」xlsxの直接URLを取得
  3. xlsxをダウンロードして raw/yakka/ に保存
  4. CSV（data/yakka_chusha_raw.csv）に変換
  5. ハッシュ比較で内容変更があれば build_master.py / export_app_data.py を実行
  6. meta.json に適用日を記録

終了コード:
  0: 更新なし（データ同一）または成功
  2: 新しいデータで再ビルド実施
  1: エラー

出典:
  https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000078916.html
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import openpyxl
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RAW_YAKKA = ROOT / "raw/yakka"
DATA = ROOT / "data"
CSV_OUT = DATA / "yakka_chusha_raw.csv"
META_APP = ROOT / "app/meta.json"
STATE = DATA / ".update_state.json"

INDEX_URL = "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000078916.html"
UA = "chusha-kahi-updater/1.0 (+medical data auto-fetch)"


def log(msg: str) -> None:
    print(f"[update_data] {msg}", flush=True)


def fetch(url: str) -> bytes:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    return r.content


def _zen2han_digit(s: str) -> str:
    """全角数字 → 半角数字"""
    return s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))


def find_latest_detail_page() -> tuple[str, str]:
    """index ページから最新の詳細ページURLと適用日表記（令和X年Y月Z日）を取得"""
    html = fetch(INDEX_URL).decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    # 「薬価基準収載品目リストについて（令和X年Y月Z日適用）」のリンクを列挙
    candidates = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        if "薬価基準収載品目リストについて" not in text:
            continue
        normalized = _zen2han_digit(text)
        m = re.search(r"令和(\d+)年\s*(\d+)月\s*(\d+)日", normalized)
        if not m:
            continue
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        western_year = 2018 + year  # 令和元年=2019
        iso = f"{western_year:04d}{month:02d}{day:02d}"
        reiwa_label = f"令和{year}年{month}月{day}日"
        href = urljoin(INDEX_URL, a["href"])
        candidates.append((iso, href, text, reiwa_label))
    if not candidates:
        raise RuntimeError("薬価基準収載品目リスト詳細ページのリンクが見つかりません")
    candidates.sort(reverse=True)
    log(f"候補: {len(candidates)}件、最新: {candidates[0][2]}")
    return candidates[0][1], candidates[0][3]


def find_chusha_xlsx_url(detail_url: str) -> str:
    """詳細ページから 注射薬 xlsx のURLを取得"""
    html = fetch(detail_url).decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    # 「注射薬」の文字の近くにある .xlsx リンクを探す
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.lower().endswith(".xlsx"):
            continue
        ctx = a.get_text(" ", strip=True)
        parent_ctx = a.parent.get_text(" ", strip=True) if a.parent else ""
        prev = a.find_previous(string=True)
        prev_text = str(prev) if prev else ""
        bag = ctx + " " + parent_ctx + " " + prev_text
        if "注射薬" in bag:
            return urljoin(detail_url, href)
    # フォールバック: URL中に _02 を含むもの（注射薬は2番目）
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".xlsx") and "_02.xlsx" in href.lower():
            return urljoin(detail_url, href)
    raise RuntimeError(f"注射薬xlsxのURLが見つかりません ({detail_url})")


def download_xlsx(url: str, applied_date: str) -> Path:
    m = re.search(r"(20\d{6})", url)
    date_tag = m.group(1) if m else "unknown"
    RAW_YAKKA.mkdir(parents=True, exist_ok=True)
    dst = RAW_YAKKA / f"yakka_chusha_{date_tag}.xlsx"
    log(f"ダウンロード: {url} -> {dst.name}")
    dst.write_bytes(fetch(url))
    return dst


def xlsx_to_csv(xlsx_path: Path, csv_path: Path) -> None:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb.active
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for row in ws.iter_rows(values_only=True):
            w.writerow(["" if c is None else c for c in row])
    log(f"CSV出力: {csv_path} ({csv_path.stat().st_size:,}B)")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def save_state(d: dict) -> None:
    STATE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def run(cmd: list[str]) -> None:
    log(f"実行: {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(f"コマンド失敗: {cmd}")


def update_meta_source(applied_date: str, xlsx_url: str) -> None:
    """app/meta.json の source_yakka に適用日を反映"""
    if not META_APP.exists():
        return
    meta = json.loads(META_APP.read_text(encoding="utf-8"))
    meta["source_yakka"] = f"{applied_date}適用 薬価基準収載品目リスト（注射薬）"
    meta["source_yakka_url"] = xlsx_url
    meta["last_updated"] = date.today().isoformat()
    META_APP.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"meta.json 更新: {applied_date}")


def main() -> int:
    state = load_state()
    try:
        detail_url, applied_date = find_latest_detail_page()
        xlsx_url = find_chusha_xlsx_url(detail_url)
    except Exception as e:
        log(f"ERROR 取得失敗: {e}")
        return 1

    prev_url = state.get("xlsx_url")
    xlsx_path = download_xlsx(xlsx_url, applied_date)
    new_hash = sha256(xlsx_path)
    prev_hash = state.get("xlsx_sha256")

    if new_hash == prev_hash:
        log(f"変更なし（ハッシュ一致, 適用日={applied_date}）")
        return 0

    log(f"新しいデータ検出: 適用日={applied_date} hash={new_hash[:12]}")
    xlsx_to_csv(xlsx_path, CSV_OUT)

    # 再ビルド
    py = str(ROOT / ".venv/bin/python3")
    if not Path(py).exists():
        py = sys.executable
    run([py, "scripts/build_master.py"])
    run([py, "scripts/export_app_data.py"])
    update_meta_source(applied_date, xlsx_url)

    save_state({
        "xlsx_url": xlsx_url,
        "xlsx_sha256": new_hash,
        "applied_date": applied_date,
        "last_updated": date.today().isoformat(),
    })
    log("再ビルド完了")
    return 2


if __name__ == "__main__":
    sys.exit(main())
