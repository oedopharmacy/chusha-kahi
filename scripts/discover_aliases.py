"""×判定の成分名を AI で告示カテゴリ照合し、見落としの alias を発見。

各成分について: 告示107号第十第一号のどのカテゴリにも該当しないか、AI に確認。
両AI が同じカテゴリを示した場合のみ alias 追加候補とする。

Output:
  data/discovered_aliases.json  AI が示唆した成分→カテゴリ対応（要レビュー）
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "data/master.csv"
CATS = ROOT / "data/kokuji_categories.json"
KOKUJI_RAW = ROOT / "data/kokuji_dai10_raw.txt"
OUT = ROOT / "data/discovered_aliases.json"


def ask_ai(cmd: str, prompt: str, model_env: str = "") -> str:
    env = os.environ.copy()
    if model_env:
        k, v = model_env.split("=", 1)
        env[k] = v
    env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"
    r = subprocess.run([cmd], input=prompt, capture_output=True, text=True, env=env, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd} rc={r.returncode}: {r.stderr.strip()[:400]}")
    return r.stdout.strip()


def parse_json_list(resp: str) -> list:
    s = resp.strip()
    if s.startswith("```"):
        s = s[s.find("\n") + 1:]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
    a = s.find("["); b = s.rfind("]")
    if a < 0 or b < 0:
        raise ValueError(f"no array: {resp[:200]}")
    return json.loads(s[a:b+1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--max-batches", type=int, default=20)
    ap.add_argument("--gemini-model", default="gemini-2.5-pro")
    ap.add_argument("--gpt-model", default="gpt-4o")
    ap.add_argument("--sleep", type=float, default=4.0)
    args = ap.parse_args()

    cats = json.loads(CATS.read_text(encoding="utf-8"))
    kokuji = KOKUJI_RAW.read_text(encoding="utf-8")
    cat_names = [c["name"] for c in cats]

    # ×判定 unique成分 + YJコード
    seen = set()
    targets = []
    with MASTER.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["院外処方可否"] != "×":
                continue
            key = r["成分名"]
            if key in seen:
                continue
            seen.add(key)
            targets.append({"成分名": r["成分名"], "yj4": r["YJコード"][:4], "販売名例": r["販売名"][:30]})

    print(f"対象成分: {len(targets)} 種類", flush=True)

    # 既存結果（resume）
    results = {}
    if OUT.exists():
        results = json.loads(OUT.read_text(encoding="utf-8"))
    todo = [t for t in targets if t["成分名"] not in results]
    print(f"未処理: {len(todo)}", flush=True)

    batches = [todo[i:i+args.batch] for i in range(0, len(todo), args.batch)]
    print(f"バッチ数: {len(batches)} (max {args.max_batches})", flush=True)

    cat_list_str = "、".join(cat_names)
    HEADER = f"""あなたは日本の医療・診療報酬制度の専門家です。

【参照】告示107号第十第一号 全文:
{kokuji}

【告示カテゴリ一覧】（{len(cat_names)}カテゴリ）
{cat_list_str}

【指示】
以下の成分名（注射薬）が、告示第十第一号のどのカテゴリにも該当するかを判定してください。
- 該当カテゴリがあれば、その正確なカテゴリ名（上記一覧から逐字一致で）を返す
- 該当しない場合は category=null
- 確信が持てない場合は category=null

**JSON配列のみで回答（前後文不要）**:
```json
[
  {{"成分名": "...", "category": "カテゴリ名 or null", "confidence": "high|medium|low"}},
  ...
]
```

【判定対象】
"""

    for bi, batch in enumerate(batches):
        if bi >= args.max_batches:
            print(f"max-batches に到達", flush=True)
            break
        block = "\n".join(f"- 成分名: {t['成分名']}  YJ4: {t['yj4']}  例: {t['販売名例']}" for t in batch)
        prompt = HEADER + block

        for ai_name, cmd, model_env in [
            ("gemini", "ask-gemini", f"GEMINI_MODEL={args.gemini_model}"),
            ("gpt", "ask-gpt", f"GPT_MODEL={args.gpt_model}"),
        ]:
            try:
                raw = ask_ai(cmd, prompt, model_env=model_env)
                parsed = parse_json_list(raw)
                for item in parsed:
                    seibun = item.get("成分名", "").strip()
                    cat = item.get("category")
                    if not seibun or not cat or cat == "null":
                        continue
                    if cat not in cat_names:
                        # fuzzy
                        for cn in cat_names:
                            if cat in cn or cn in cat:
                                cat = cn
                                break
                    if cat in cat_names:
                        d = results.setdefault(seibun, {})
                        d[ai_name] = {"category": cat, "confidence": item.get("confidence")}
                print(f"[{bi+1}/{len(batches)}][{ai_name}] {len(parsed)} 件", flush=True)
            except Exception as e:
                print(f"[{bi+1}/{len(batches)}][{ai_name}] ERROR: {str(e)[:200]}", flush=True)
            time.sleep(args.sleep)

        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 集計
    print("\n=== 結果集計 ===")
    both = [(k, v) for k, v in results.items() if "gemini" in v and "gpt" in v]
    agree = [(k, v) for k, v in both if v["gemini"]["category"] == v["gpt"]["category"]]
    print(f"両AI記入: {len(both)} / うち一致: {len(agree)}")
    print("\n=== 両AI一致カテゴリ TOP ===")
    from collections import Counter
    c = Counter(v["gemini"]["category"] for k, v in agree)
    for cat, n in c.most_common(15):
        print(f"  [{cat}]: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
