#!/usr/bin/env python3
"""
recall — semantic search over the memory files (the optional third retrieval channel).

The boot layer (BRAIN) is the always-loaded map; grep handles exact names; this handles
*meaning* — "what did we work on around X?" where the exact keyword escapes you. It is
NOT a replacement for either: it returns PATHS + snippets, not full file contents, so the
agent then opens only the one or two files worth reading. (Returning paths, not bodies,
also keeps the context small — you don't pour whole files into the window to find one.)

LOCAL and offline, no API. The index must exist first (run embed.py). Run via the venv:
  scripts/recall/.venv/bin/python scripts/recall/recall.py "<query>" [--k 8] [--json]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# offline — the model is already cached by embed.py; no Hugging Face pings
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

REPO_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = REPO_ROOT / "memory"
INDEX_DIR = MEMORY_DIR / ".index"
EMB_PATH = INDEX_DIR / "recall.npz"
META_PATH = INDEX_DIR / "recall.meta.json"


def stale_warning(meta):
    """Warn if any active file is newer than the index (drift)."""
    try:
        newest = 0.0
        for p in meta.get("mtimes", {}):
            fp = MEMORY_DIR / p
            if fp.exists():
                newest = max(newest, fp.stat().st_mtime)
        stored = max(meta.get("mtimes", {}).values(), default=0.0)
        if newest > stored + 1.0:
            print("note: index may be stale (memory changed since last embed) — "
                  "re-run: scripts/recall/.venv/bin/python scripts/recall/embed.py --incremental",
                  file=sys.stderr)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="natural-language query")
    ap.add_argument("--k", type=int, default=8, help="number of results (default 8)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--min-score", type=float, default=0.0, help="score threshold")
    args = ap.parse_args()

    if not EMB_PATH.exists() or not META_PATH.exists():
        print("No index. Build it first: scripts/recall/.venv/bin/python scripts/recall/embed.py",
              file=sys.stderr)
        sys.exit(1)

    import numpy as np
    emb = np.load(EMB_PATH)["emb"]
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    chunks = meta["chunks"]
    stale_warning(meta)

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(meta.get("model"))  # auto-selects cuda / mps / cpu

    q = model.encode(["query: " + args.query], normalize_embeddings=True).astype(np.float32)[0]
    scores = emb @ q  # cosine (both normalized) — brute force; fine for a few hundred vectors

    # best chunk per file (dedupe)
    best = {}
    for i, ch in enumerate(chunks):
        s = float(scores[i])
        p = ch["path"]
        if p not in best or s > best[p]["score"]:
            best[p] = {"path": p, "heading": ch["heading"], "score": s,
                       "snippet": ch["snippet"], "type": ch["type"],
                       "last_edited": ch["last_edited"]}
    ranked = sorted(best.values(), key=lambda x: x["score"], reverse=True)
    ranked = [r for r in ranked if r["score"] >= args.min_score][:args.k]

    if args.json:
        print(json.dumps(ranked, ensure_ascii=False))
        return

    if not ranked:
        print("Nothing relevant. Try grep, or rephrase the query.")
        return
    for r in ranked:
        head = f"  ## {r['heading']}" if r["heading"] else ""
        print(f"[{r['score']:.3f}] memory/{r['path']}{head}")
        print(f"        {r['snippet']}")


if __name__ == "__main__":
    main()
