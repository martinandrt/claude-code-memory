#!/usr/bin/env python3
"""
embed — build a local semantic index of the memory files.

OPTIONAL add-on. The core system (grep + the boot layer) needs none of this. Reach
for it only when grep stops being enough — usually a few hundred files in, when you
want "what did we work on around X?" and the exact keyword escapes you.

Walks the active memory .md files (same scan logic as memory-index.py: skips the
boot layer + archive + dot-dirs), chunks them, encodes each chunk with a local model
(intfloat/multilingual-e5-large), and writes the vectors to memory/.index/.

LOCAL and offline. The model downloads once from Hugging Face into ~/.cache, then runs
with no network. No API key. Needs the deps in requirements.txt (sentence-transformers,
numpy) — install them in a venv, ideally:

  python3 -m venv scripts/recall/.venv
  scripts/recall/.venv/bin/pip install -r scripts/recall/requirements.txt
  scripts/recall/.venv/bin/python scripts/recall/embed.py

  embed.py                 # full rebuild
  embed.py --incremental   # re-embed only files whose mtime changed
  embed.py --stats         # print index status, change nothing
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = REPO_ROOT / "memory"
INDEX_DIR = MEMORY_DIR / ".index"
EMB_PATH = INDEX_DIR / "recall.npz"
META_PATH = INDEX_DIR / "recall.meta.json"

MODEL_NAME = "intfloat/multilingual-e5-large"
# Skip the always-loaded boot layer (already in context, no point recalling it) and the
# generated index. Add any private files you keep out of the public/shared index here.
SKIP_FILES = {"MEMORY.md", "LINEAGE.md", "BRAIN.md"}
DENSE_WORDS = 1000  # above this many words → split the file by its ## headings


def parse_doc(path: Path):
    """Return (frontmatter dict, body without frontmatter)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}, ""
    m = re.match(r"^---\n(.+?)\n---\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm, m.group(2)


def scan_files():
    """Active memory files (same filters as memory-index.py)."""
    out = []
    for path in sorted(MEMORY_DIR.rglob("*.md")):
        if path.name in SKIP_FILES:
            continue
        rel = path.relative_to(MEMORY_DIR)
        if rel.parts[0] == "archive":
            continue
        if any(part.startswith(".") for part in rel.parts):
            continue
        out.append((path, rel))
    return out


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def chunk_file(path: Path, rel: Path):
    """Return a list of chunks: {path, heading, text, snippet, type, last_edited}."""
    fm, body = parse_doc(path)
    name = fm.get("name", rel.stem)
    desc = fm.get("description", "")
    ftype = fm.get("type", "unknown")
    ledit = fm.get("last_edited", "")
    prefix = f"{name}. {desc}".strip()

    words = len(body.split())
    chunks = []
    if words > DENSE_WORDS and "\n## " in body:
        # dense → split by H2; each section keeps the (name + desc) prefix for precision
        for part in re.split(r"\n(?=## )", body):
            t = part.strip()
            if not t:
                continue
            hm = re.match(r"##\s+(.+)", t)
            heading = clean(hm.group(1)) if hm else ""
            chunks.append({
                "path": str(rel), "heading": heading,
                "text": f"{prefix}\n\n{t}".strip(), "snippet": clean(t)[:180],
                "type": ftype, "last_edited": ledit,
            })
    else:
        chunks.append({
            "path": str(rel), "heading": "",
            "text": f"{prefix}\n\n{body}".strip(), "snippet": clean(desc or body)[:180],
            "type": ftype, "last_edited": ledit,
        })
    return chunks


def load_existing():
    if EMB_PATH.exists() and META_PATH.exists():
        import numpy as np
        return np.load(EMB_PATH)["emb"], json.loads(META_PATH.read_text(encoding="utf-8"))
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--incremental", action="store_true")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    import numpy as np

    if args.stats:
        emb, meta = load_existing()
        if meta is None:
            print("No index yet. Run a full build first.")
            return
        files = sorted({m["path"] for m in meta["chunks"]})
        print(f"Index: {len(meta['chunks'])} chunks from {len(files)} files")
        print(f"Model: {meta.get('model')}  |  built: {meta.get('built_at')}")
        print(f"Embedding shape: {emb.shape}")
        return

    files = scan_files()
    cur_mtime = {str(rel): path.stat().st_mtime for path, rel in files}

    reuse_emb_rows, reuse_chunks = [], []
    to_encode_files = files
    if args.incremental:
        old_emb, old_meta = load_existing()
        if old_meta is not None:
            old_mtime = old_meta.get("mtimes", {})
            unchanged = {p for p in cur_mtime
                         if p in old_mtime and abs(old_mtime[p] - cur_mtime[p]) < 1e-6}
            for i, ch in enumerate(old_meta["chunks"]):
                if ch["path"] in unchanged:
                    reuse_emb_rows.append(old_emb[i])
                    reuse_chunks.append(ch)
            to_encode_files = [(p, r) for p, r in files if str(r) not in unchanged]
            print(f"Incremental: {len(unchanged)} files unchanged, {len(to_encode_files)} to re-embed.")

    new_chunks = []
    for path, rel in to_encode_files:
        new_chunks.extend(chunk_file(path, rel))

    print(f"Encoding {len(new_chunks)} chunks with {MODEL_NAME} …")
    new_emb = np.zeros((0, 1024), dtype=np.float32)
    if new_chunks:
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(MODEL_NAME)  # auto-selects cuda / mps / cpu
        passages = ["passage: " + c["text"] for c in new_chunks]  # e5 requires the "passage:" prefix
        new_emb = model.encode(passages, normalize_embeddings=True,
                               batch_size=16, show_progress_bar=False).astype(np.float32)
        print(f"Encoded on device: {model.device}")

    if reuse_emb_rows:
        all_emb = (np.vstack([np.array(reuse_emb_rows, dtype=np.float32), new_emb])
                   if len(new_emb) else np.array(reuse_emb_rows, dtype=np.float32))
        all_chunks = reuse_chunks + new_chunks
    else:
        all_emb, all_chunks = new_emb, new_chunks

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(EMB_PATH, emb=all_emb)
    META_PATH.write_text(json.dumps({
        "model": MODEL_NAME,
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mtimes": cur_mtime,
        "chunks": all_chunks,
    }, ensure_ascii=False), encoding="utf-8")

    print(f"Index saved: {len(all_chunks)} chunks from {len(files)} files → {EMB_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
