"""Find and resolve the "research:" citations in notes.yaml, appendix.yaml and content.yaml.

A citation looks like ``research: reports/libraries.md section 1 (L/08_extra_checks.py, ...)``. It runs from
"research:" to the next ";", double quote or line end outside parentheses. Inside it, every token that looks
like a file name is a reference. Bare names (``copc_remote.txt``) resolve against the directory of the
previous reference in the same citation, ``L/`` is the libraries report's alias for ``libraries/``, and a name
that still does not resolve is looked up by its base name (only if exactly one file has it).

The research files live in ``docs/research/`` (copied from the session scratchpad, same sub-paths).
Used by ``docs/research/collect.py`` (copy) and ``deck/qa/checks.py`` (every cited file must exist).
"""

from __future__ import annotations

import glob
import re
from pathlib import Path

FILE_RE = re.compile(r"(?<![\w/.*-])((?:[\w.*-]+/)*[\w*-][\w.*-]*\.(?:md|json|txt|py|out|log|patch|cpp|csv|html))\b")
PROJECT_PREFIXES = ("results/", "snippets/", "pipeline/", "deck/", "renders/", "bench/", "data/", "docs/")
PROJECT_FILES = {"storyboard.md", "CONTRACTS.md", "README.md", "content.yaml", "notes.yaml", "appendix.yaml"}
ALIASES = {"L/": "libraries/"}
SKIP_DIRS = {"pt3d-src", "pt3d-src-cxx20", "pt3d-venv", "laspy-only-venv", "venv", ".venv", "__pycache__", "inspect"}


def citations(text: str) -> list[str]:
    """The text of every "research:" citation in ``text``."""
    out = []
    for m in re.finditer(r"research:", text):
        seg, depth = [], 0
        for ch in text[m.end():]:
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            elif ch in ';"\n' and depth == 0:
                break
            seg.append(ch)
        s = "".join(seg)
        nxt = s.find("research:")
        out.append(s[:nxt] if nxt >= 0 else s)
    return out


def _by_basename(root: Path, name: str) -> list[Path]:
    hits = []
    for p in root.rglob(name):
        if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_DIRS):
            hits.append(p)
    return hits


def resolve(text: str, root: Path) -> tuple[list[str], list[str]]:
    """(resolved paths relative to root, unresolved tokens) for all research citations in ``text``.
    Globs (``libraries/pypi/*.json``) resolve to every match."""
    root = Path(root)
    found, missing = [], []
    for cit in citations(text):
        last_dir = None
        for tok in FILE_RE.findall(cit):
            if tok.startswith(PROJECT_PREFIXES) or tok in PROJECT_FILES:
                continue
            for a, b in ALIASES.items():
                if tok.startswith(a):
                    tok = b + tok[len(a):]
            cands = [tok]
            if "/" not in tok and last_dir:
                cands.insert(0, f"{last_dir}/{tok}")
            hit = None
            for c in cands:
                if "*" in c:
                    g = sorted(glob.glob(str(root / c)))
                    if g:
                        found += [str(Path(x).relative_to(root)) for x in g]
                        hit = c
                        break
                elif (root / c).is_file():
                    hit = c
                    found.append(c)
                    break
            if hit is None and "*" not in tok:
                hits = _by_basename(root, Path(tok).name)
                if len(hits) == 1:
                    hit = str(hits[0].relative_to(root))
                    found.append(hit)
            if hit is None:
                missing.append(tok)
                continue
            last_dir = str(Path(hit).parent) if "/" in hit else last_dir
    return sorted(set(found)), sorted(set(missing))


def yaml_texts(*paths: Path) -> str:
    """All text of the given YAML files (comments included), for citation scanning."""
    return "\n".join(Path(p).read_text(encoding="utf-8") for p in paths if Path(p).exists())
