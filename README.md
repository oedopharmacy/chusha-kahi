# 注射薬 院外処方可否 検索ツール

在宅医療クリニック向けの注射薬院外処方可否検索ツール。
ひらがな・カタカナ・半角カナ・全角英数のいずれでも薬品名・成分名を検索可能。

**公開URL**: https://chusha-kahi.oedo-daita.workers.dev

## 判定根拠（エビデンス）

以下の公的資料の機械突合により判定しています：

- **薬価基準収載品目リスト（注射薬）**
  厚生労働省公開、毎月更新
  https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000078916.html

- **平成18年厚生労働省告示第107号** 第十（療担規則第20条第二号トの注射薬）
  在宅医療で院外処方可能な注射薬カテゴリの限定列挙

判定区分:
- **○ 院外可**: 告示第十第一号のカテゴリに該当
- **× 院内のみ**: 告示非該当（注射薬の原則は院内処方）
- **－ 削除**: 告示別表2収載（保険使用不可）

## アーキテクチャ

```
raw/yakka/      薬価基準xlsx原典（MHLW公開）
raw/kokuji/     告示107号 原典HTML
    ↓
scripts/
  update_data.py     MHLWから最新xlsx取得→CSV変換→再ビルド
  build_master.py    告示カテゴリ × 成分名 突合 → 判定
  export_app_data.py マスタCSV → app/data.json
    ↓
app/
  index.html     スマホ対応 検索UI
  data.json      全品目の判定結果
  meta.json      出典情報・更新日
    ↓
Cloudflare Workers (wrangler deploy)
```

## ローカル開発

```bash
# 依存セットアップ
python3 -m venv .venv
.venv/bin/pip install openpyxl requests beautifulsoup4 lxml PyYAML

# 最新データ取得＋再ビルド
.venv/bin/python scripts/update_data.py

# ローカル表示（ポート8765）
python3 -m http.server 8765 --directory app
open http://localhost:8765/

# デプロイ
wrangler deploy
```

## 自動更新

GitHub Actions により毎月 1日・15日・25日 JST 午前3時に実行：
1. MHLWページから最新の注射薬xlsx URL を取得
2. ダウンロード＋ハッシュ比較で変更検知
3. 変更があれば再ビルド→自動デプロイ

必要なシークレット（GitHub Repository Settings → Secrets）:
- `CLOUDFLARE_API_TOKEN`: Workers Deploy 権限のトークン
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare アカウントID

## 免責

本ツールは告示テキストと薬価基準の機械突合による参考情報です。
最終判定は必ず薬剤師・医師が添付文書・告示原文をご確認ください。
返戻責任は利用者に帰属します。
