"""片AIのみ示唆された成分を、両AIに対して個別（バッチ小）で再確認。

ハルシネーション抑止のため、両AIが同じカテゴリを返した場合のみ採用。
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DISC = ROOT / "data/discovered_aliases.json"
CATS = ROOT / "data/kokuji_categories.json"
KOKUJI_RAW = ROOT / "data/kokuji_dai10_raw.txt"
OUT = ROOT / "data/recheck_aliases.json"


def ask_ai(cmd: str, prompt: str, model_env: str = "") -> str:
    env = os.environ.copy()
    if model_env:
        k, v = model_env.split("=", 1)
        env[k] = v
    env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"
    r = subprocess.run([cmd], input=prompt, capture_output=True, text=True, env=env, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd} rc={r.returncode}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def parse_json_obj(resp: str) -> dict:
    s = resp.strip()
    if s.startswith("```"):
        s = s[s.find("\n") + 1:]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
    a = s.find("{"); b = s.rfind("}")
    if a < 0 or b < 0:
        raise ValueError(f"no obj: {resp[:200]}")
    return json.loads(s[a:b+1])


def main() -> int:
    disc = json.loads(DISC.read_text(encoding="utf-8"))
    cats = json.loads(CATS.read_text(encoding="utf-8"))
    cat_names = [c["name"] for c in cats]
    kokuji = KOKUJI_RAW.read_text(encoding="utf-8")
    cat_list_str = "、".join(cat_names)

    # 片AIのみ示唆 + 両AI不一致 を再確認対象に
    targets = []
    for k, v in disc.items():
        g = (v.get("gemini") or {}).get("category")
        p = (v.get("gpt") or {}).get("category")
        if (g and not p) or (p and not g) or (g and p and g != p):
            targets.append(k)
    print(f"再確認対象: {len(targets)}成分", flush=True)

    results = {}
    if OUT.exists():
        results = json.loads(OUT.read_text(encoding="utf-8"))

    HEADER = f"""あなたは日本の医療・診療報酬制度の専門家です。

【告示原文】
{kokuji}

【告示カテゴリ一覧】
{cat_list_str}

【指示】
以下の1成分について、告示第十第一号のどのカテゴリに該当するかを厳密に判定してください。
- 該当が確実なら category=正確なカテゴリ名（一覧から逐字一致）
- 該当しない or 不明確 → category=null
- ハルシネーションを避け、確実な場合のみ回答

JSON形式で回答（前後文不要）:
```json
{{"成分名": "...", "category": "..." or null, "confidence": "high|medium|low", "reason": "判定理由50字以内"}}
```

【判定対象成分】
"""

    for i, seibun in enumerate(targets):
        if seibun in results and "gemini" in results[seibun] and "gpt" in results[seibun]:
            continue
        prompt = HEADER + f"成分名: {seibun}"
        r_data = results.setdefault(seibun, {})
        for ai, cmd, env in [
            ("gemini", "ask-gemini", "GEMINI_MODEL=gemini-2.5-pro"),
            ("gpt", "ask-gpt", "GPT_MODEL=gpt-4o"),
        ]:
            if ai in r_data:
                continue
            try:
                raw = ask_ai(cmd, prompt, model_env=env)
                obj = parse_json_obj(raw)
                cat = obj.get("category")
                if cat and cat not in cat_names:
                    for cn in cat_names:
                        if cat in cn or cn in cat:
                            cat = cn
                            break
                r_data[ai] = {
                    "category": cat if cat in cat_names else None,
                    "confidence": obj.get("confidence"),
                    "reason": obj.get("reason"),
                }
                print(f"[{i+1}/{len(targets)}][{ai}] {seibun[:30]} → {cat}", flush=True)
            except Exception as e:
                print(f"[{i+1}/{len(targets)}][{ai}] ERROR: {str(e)[:200]}", flush=True)
                r_data[ai] = {"error": str(e)[:200]}
            time.sleep(2.0)
        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 集計
    print("\n=== recheck 結果 ===")
    both_agree = []
    for k, v in results.items():
        g = (v.get("gemini") or {}).get("category")
        p = (v.get("gpt") or {}).get("category")
        if g and p and g == p:
            both_agree.append((k, g))
    print(f"両AI一致: {len(both_agree)}成分")
    from collections import Counter
    c = Counter(cat for _, cat in both_agree)
    for cat, n in c.most_common():
        print(f"  [{cat}]: {n}成分")
    return 0


if __name__ == "__main__":
    sys.exit(main())
