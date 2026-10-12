"""Copy every research file that deck/notes.yaml, deck/appendix.yaml or deck/content.yaml cites with
"research:" from the session scratchpad into docs/research/ (same sub-paths), so the traces survive the
session. Files larger than MAX_BYTES (point clouds, build trees) are not copied and are listed instead.

Run once:  uv run python docs/research/collect.py <scratchpad dir>
Writes docs/research/MANIFEST.json (copied files with size and sha256, skipped and unresolved references).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TALK = HERE.parents[1]
sys.path.insert(0, str(TALK / "deck"))
from lib.research_refs import resolve, yaml_texts  # noqa: E402

MAX_BYTES = 5_000_000
SOURCES = [TALK / "deck" / "notes.yaml", TALK / "deck" / "appendix.yaml", TALK / "deck" / "content.yaml"]
EXTRA = ["libraries/out_03_open3d_tensor.txt", "libraries/out_07_torch.txt"]  # raw outputs behind B3


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]).resolve()
    found, missing = resolve(yaml_texts(*SOURCES), src)
    copied, skipped = [], []
    for rel in sorted(set(found) | set(EXTRA)):
        p = src / rel
        if not p.is_file():
            missing.append(rel)
            continue
        if p.stat().st_size > MAX_BYTES:
            skipped.append({"path": rel, "bytes": p.stat().st_size})
            continue
        dst = HERE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
        copied.append({"path": rel, "bytes": p.stat().st_size,
                       "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    manifest = {"source": "session scratchpad (research reports and prototype runs)",
                "copied": copied, "skipped_too_large": skipped, "unresolved": sorted(set(missing))}
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"copied {len(copied)} files, skipped {len(skipped)}, unresolved {sorted(set(missing))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
