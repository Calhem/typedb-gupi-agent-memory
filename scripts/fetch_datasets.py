"""Download the benchmark datasets into .data/ (git-ignored) and verify their checksums.

    uv run python -I scripts/fetch_datasets.py

Pinned to the versions recorded in docs/datasets.md. Read the licences there before use (LoCoMo is
CC BY-NC 4.0: non-commercial research only).
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / ".data"
FILES = [
    ("locomo/locomo10.json",
     "https://raw.githubusercontent.com/snap-research/locomo/cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc/data/locomo10.json",
     "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"),
    ("longmemeval/longmemeval_s_cleaned.json",
     "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json",
     "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"),
    ("longmemeval/longmemeval_oracle.json",
     "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_oracle.json",
     "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c"),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ok = True
    for rel, url, expected in FILES:
        path = ROOT / rel
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            print(f"downloading {rel} ...", flush=True)
            urllib.request.urlretrieve(url, path)
        actual = sha256(path)
        status = "ok" if actual == expected else "CHECKSUM MISMATCH"
        ok &= actual == expected
        print(f"{status}  {rel}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
