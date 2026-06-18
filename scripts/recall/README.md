# Optional: semantic recall

A third retrieval channel, for when `grep` stops being enough.

The core memory system has two ways to find things, and needs nothing else:

- **BRAIN.md** — the always-loaded map. The agent reads it every session.
- **grep** — exact names: a skill, a client, a filename.

That covers most days. But past a few hundred files there's a gap: *"what did we work
on around X?"* when you can't remember the exact word. grep wants the literal token;
you have the meaning. This layer fills that gap — a local vector index you query in
plain language.

It is deliberately **off to the side**. The promise the main README makes — plain
files, no infra, no API key, nothing to install — is about the *core*. This add-on
keeps the no-API-key and fully-local part, but it does add one real dependency
(`sentence-transformers`) and a small on-disk vector store. That's the trade. Adopt it
only if you feel the gap; ignore the whole folder otherwise.

## What it is

- **Model:** `intfloat/multilingual-e5-large` (MIT, 1024-dim, works across languages).
  Downloads once from Hugging Face into `~/.cache`, then runs offline.
- **Store:** `memory/.index/recall.npz` + `recall.meta.json` — gitignored, regenerable.
  A few hundred files is ~1–2 MB. Brute-force cosine; a query is milliseconds. No
  FAISS, no Chroma — needless for this many vectors.
- **Returns paths, not bodies.** You get the top files + a one-line snippet each; the
  agent then opens the one or two worth reading. It's a finder, not a chatbot over your
  memory.

## Setup

```bash
python3 -m venv scripts/recall/.venv
scripts/recall/.venv/bin/pip install -r scripts/recall/requirements.txt
scripts/recall/.venv/bin/python scripts/recall/embed.py        # build the index (first run downloads the model)
```

## Use

```bash
# search
scripts/recall/.venv/bin/python scripts/recall/recall.py "how do we handle invoicing" --k 8

# keep the index fresh — cheap, only re-embeds changed files (wire into /session-end)
scripts/recall/.venv/bin/python scripts/recall/embed.py --incremental
```

## Honest limits

- **Weak on exact names** (skills, people, identifiers): e5 is dense-only, no sparse
  term match. Treat it as a hybrid — recall narrows, then grep / read confirms.
- **Archive is excluded** by default (old session dumps would drown out active memory).
- **The `query:` / `passage:` prefixes are mandatory** for e5 — they're baked into the
  scripts; drop them and quality silently degrades.
- It returns candidates; **you** still do the synthesis.
