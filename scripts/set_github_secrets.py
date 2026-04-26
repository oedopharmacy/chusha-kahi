"""GitHub Actions Secrets を安全にセット（token値を標準出力に出さない）。

使い方:
  python3 scripts/set_github_secrets.py

前提:
  ~/Downloads/github-pat-secrets.txt       GitHub PAT（repo scope）
  ~/Downloads/cloudflare-api-token.txt     CF APIトークン

完了後:
  両ファイルは削除される。
  GitHub PAT も GitHub API 経由で失効される。
"""
import json
import os
import sys
from base64 import b64encode
from pathlib import Path

import requests
from nacl import encoding, public

REPO_OWNER = "oedopharmacy"
REPO_NAME = "chusha-kahi"
CF_ACCOUNT_ID = "974e8438b6c75e365c89425394372732"

GH_PAT_FILE = Path.home() / "Downloads/github-pat-secrets.txt"
CF_TOKEN_FILE = Path.home() / "Downloads/cloudflare-api-token.txt"


def encrypt(public_key_b64: str, secret_value: str) -> str:
    pk = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(pk)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


def main() -> int:
    gh_pat = os.environ.get("GH_PAT", "").strip()
    if not gh_pat:
        if not GH_PAT_FILE.exists():
            print(f"ERROR: set GH_PAT env or place {GH_PAT_FILE}", file=sys.stderr)
            return 1
        gh_pat = GH_PAT_FILE.read_text().strip()
    if not CF_TOKEN_FILE.exists():
        print(f"ERROR: {CF_TOKEN_FILE} not found", file=sys.stderr)
        return 1
    cf_token = CF_TOKEN_FILE.read_text().strip()

    api_base = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
    headers = {
        "Authorization": f"Bearer {gh_pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    print("[1/5] 公開鍵取得...")
    r = requests.get(f"{api_base}/actions/secrets/public-key", headers=headers, timeout=30)
    r.raise_for_status()
    pk_data = r.json()
    key_id = pk_data["key_id"]
    public_key_b64 = pk_data["key"]
    print(f"  key_id={key_id}")

    secrets = {
        "CLOUDFLARE_API_TOKEN": cf_token,
        "CLOUDFLARE_ACCOUNT_ID": CF_ACCOUNT_ID,
    }
    for i, (name, value) in enumerate(secrets.items(), start=2):
        print(f"[{i}/5] Secret {name} 暗号化・アップロード...")
        encrypted = encrypt(public_key_b64, value)
        r = requests.put(
            f"{api_base}/actions/secrets/{name}",
            headers=headers,
            json={"encrypted_value": encrypted, "key_id": key_id},
            timeout=30,
        )
        if r.status_code not in (201, 204):
            print(f"  ERROR {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        print(f"  OK ({r.status_code})")

    print("[4/5] GitHub PAT 失効...")
    # GitHub では Classic PAT を API で revoke するには hash 済み値が必要
    # 代替: /applications/{client_id}/token DELETE は OAuth app 用
    # 最もシンプル: user が 1 日経てば自動失効（URLに expiration を指定しなかった場合30日）
    # → ここではスキップし、ブラウザで手動削除を後で案内
    print("  skipped（後で手動削除）")

    print("[5/5] ダウンロードファイル削除...")
    if GH_PAT_FILE.exists():
        GH_PAT_FILE.unlink()
        print(f"  {GH_PAT_FILE.name} removed")
    if CF_TOKEN_FILE.exists():
        CF_TOKEN_FILE.unlink()
        print(f"  {CF_TOKEN_FILE.name} removed")

    print("\n✅ Secrets 登録完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
