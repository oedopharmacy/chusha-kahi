"""3者(Claude/Gemini/GPT)の判定を比較し、各カテゴリの consensus 判定を生成。

ロジック:
  - 3者一致 → confidence "high", verdict = 一致値
  - 2/3一致 → confidence "medium", verdict = 多数派
  - 全員不一致 → confidence "low", verdict = "△" (要確認)
  - 抗悪性腫瘍剤・注射用抗菌薬・電解質製剤 等の薬効分類包括カテゴリで全AI ○ 判定 →
    Claude の意図的 △ を尊重するか consensus に従うかは confidence で示す

Output:
  data/consensus.json  カテゴリ別 consensus 判定 + 3AI 意見 + reason / method / source
"""
from __future__ import annotations

import json
import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEMINI = ROOT / "data/gemini_verification.json"
GPT = ROOT / "data/gpt_verification.json"
CATS = ROOT / "data/kokuji_categories.json"
MASTER = ROOT / "data/master.csv"
OUT = ROOT / "data/consensus.json"


import re
# 漢字 + ひらがな1文字以上 + 漢字 → ひらがなを除去（ルビ表記）
_RUBY_RE = re.compile(r"([一-龠])([ぁ-ん]+)(?=[一-龠])")


def normalize_cat(name: str) -> str:
    """カテゴリ名のふりがな揺れと空白類を除去して比較キー化"""
    s = name
    prev = None
    while prev != s:
        prev = s
        s = _RUBY_RE.sub(r"\1", s)
    # 全種類の空白を除去（半角・全角・nbsp・タブ等）
    s = re.sub(r"[\s 　]", "", s)
    return s


def load_current_claude_verdicts() -> dict:
    """master.csv（現在のClaude判定）からカテゴリ別最頻値を取得（正規化キー）"""
    verdicts = defaultdict(Counter)
    with MASTER.open(encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            reason = r["判定根拠"]
            if "[" not in reason or "]" not in reason:
                continue
            inner = reason.split("[", 1)[1].split("]", 1)[0]
            for cat in inner.split("/"):
                key = normalize_cat(cat.strip())
                verdicts[key][r["院外処方可否"]] += 1
    return {cat: c.most_common(1)[0][0] for cat, c in verdicts.items()}


def main() -> int:
    cats = json.loads(CATS.read_text(encoding="utf-8"))
    gem = json.loads(GEMINI.read_text(encoding="utf-8")) if GEMINI.exists() else {}
    gpt = json.loads(GPT.read_text(encoding="utf-8")) if GPT.exists() else {}
    current_claude = load_current_claude_verdicts()

    consensus = {}
    stats = Counter()
    for c in cats:
        name = c["name"]
        g_item = gem.get(name, {})
        p_item = gpt.get(name, {})
        g_v = g_item.get("verdict")
        p_v = p_item.get("verdict")
        # Claude判定: 現在の master.csv から取得（カテゴリ名正規化）
        c_v = (
            current_claude.get(normalize_cat(name))
            or g_item.get("claude_verdict")
            or p_item.get("claude_verdict")
        )

        # consensus 計算
        verdicts = [v for v in (c_v, g_v, p_v) if v and v != "?"]
        confidence = "unknown"
        consensus_v = None
        if not verdicts:
            confidence = "unknown"
            consensus_v = None
        else:
            c2 = Counter(verdicts)
            top, top_count = c2.most_common(1)[0]
            if len(verdicts) == 3 and top_count == 3:
                confidence = "high"
                consensus_v = top
            elif top_count >= 2:
                confidence = "medium"
                consensus_v = top
            else:
                # 全員不一致
                confidence = "low"
                consensus_v = "△"

        # source / reason / method は GPT を優先（最新）、なければ Gemini
        consensus[name] = {
            "consensus_verdict": consensus_v,
            "confidence": confidence,
            "verdicts": {"claude": c_v, "gemini": g_v, "gpt": p_v},
            "reason_why_gemini": g_item.get("reason_why", ""),
            "reason_why_gpt": p_item.get("reason_why", ""),
            "method_gemini": g_item.get("prescription_method") or "",
            "method_gpt": p_item.get("prescription_method") or "",
            "source_text": p_item.get("source_text") or g_item.get("source_text", ""),
            "kokuji_condition": c.get("condition") or "",
        }
        stats[(c_v, g_v, p_v)] += 1
        stats[("conf", confidence)] += 1

    OUT.write_text(json.dumps(consensus, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {OUT}")
    print(f"\n=== confidence 分布 ===")
    for k, v in stats.items():
        if isinstance(k, tuple) and k[0] == "conf":
            print(f"  {k[1]}: {v}")
    print(f"\n=== 3者の verdict 組合せ TOP 10 ===")
    pat = {k: v for k, v in stats.items() if isinstance(k, tuple) and k[0] != "conf"}
    for (c, g, p), n in sorted(pat.items(), key=lambda x: -x[1])[:10]:
        print(f"  Claude={c} Gemini={g} GPT={p}: {n}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
