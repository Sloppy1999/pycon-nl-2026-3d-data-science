"""Structure-first step: unpack the PyCon NL 2026 master, duplicate its example slide for each deck slide's
layout with the pptx skill's add_slide.py, set <p:sldIdLst>, rebuild sections, drop any add-in part, clean, pack.
The master's example slides (one per layout, section "Layout examples") end up unreferenced and clean.py removes
them."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import quoteattr

PPTX_SKILL = Path(os.environ.get("PPTX_SKILL_DIR", Path.home() / ".claude/skills/pptx"))
SCRIPTS = PPTX_SKILL / "scripts"
NS_UUID = uuid.UUID("6f1c2a43-3d5e-4a8e-9b7c-20261015abcd")   # fixed namespace: deterministic ids


def _run_script(script: str, *args: str) -> str:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SCRIPTS) + os.pathsep + env.get("PYTHONPATH", "")
    res = subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=str(SCRIPTS),
                         env=env, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"{script} failed: {res.stderr.strip() or res.stdout.strip()}")
    return res.stdout


def unpack(src: Path, dest: Path):
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with zipfile.ZipFile(src) as zf:
        zf.extractall(dest)


def pack(src_dir: Path, out: Path):
    """Deterministic zip: fixed timestamps, [Content_Types].xml first, sorted entries."""
    if out.exists():
        out.unlink()
    files = sorted(p for p in src_dir.rglob("*") if p.is_file())
    files.sort(key=lambda p: (p.name != "[Content_Types].xml", str(p.relative_to(src_dir))))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            info = zipfile.ZipInfo(str(p.relative_to(src_dir)).replace(os.sep, "/"), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, p.read_bytes())


def example_slide_for_layout(u: Path) -> dict[int, str]:
    """Map layout number -> example slide file, by reading each example slide's layout rel."""
    out = {}
    for rel in sorted((u / "ppt/slides/_rels").glob("slide*.xml.rels")):
        m = re.search(r'slideLayouts/slideLayout(\d+)\.xml', rel.read_text(encoding="utf-8"))
        if m:
            out.setdefault(int(m.group(1)), rel.name.replace(".rels", ""))
    return out


def remove_webextension(u: Path) -> list[str]:
    """Drop any add-in task pane part and the template thumbnail, should a master carry them (PowerPoint
    regenerates the thumbnail on save). The PyCon NL master has neither; kept as a guard."""
    removed = []
    for rel in ("ppt/webextensions",):
        p = u / rel
        if p.exists():
            shutil.rmtree(p)
            removed.append(rel)
    thumb = u / "docProps/thumbnail.jpeg"
    if thumb.exists():
        thumb.unlink()
        removed.append("docProps/thumbnail.jpeg")
    root_rels = u / "_rels/.rels"
    x = root_rels.read_text(encoding="utf-8")
    x = re.sub(r'<Relationship [^>]*webextensiontaskpanes[^>]*/>', "", x)
    x = re.sub(r'<Relationship [^>]*metadata/thumbnail[^>]*/>', "", x)
    root_rels.write_text(x, encoding="utf-8")
    ct = u / "[Content_Types].xml"
    x = ct.read_text(encoding="utf-8")
    x = re.sub(r'<Override PartName="/ppt/webextensions/[^"]*"[^>]*/>', "", x)
    ct.write_text(x, encoding="utf-8")
    return removed


def build_structure(template: Path, work: Path, plan: list[dict]) -> tuple[Path, list[str]]:
    """plan: [{"key": "1", "layout": 1, "section": "Hook"}, ...] in deck order.
    Returns (structure.pptx, log lines)."""
    log = []
    u = work / "unpacked"
    unpack(template, u)
    examples = example_slide_for_layout(u)
    log.append(f"example slides per layout: {examples}")
    new_files = []
    for item in plan:
        src = examples[int(item["layout"])]
        out = (_run_script("add_slide.py", str(u), src) if (SCRIPTS / "add_slide.py").exists()
               else _duplicate_slide(u, src))
        m = re.search(r"Created ppt/slides/(slide\d+\.xml)", out)
        if not m:
            raise RuntimeError(f"add_slide.py output not understood: {out}")
        new_files.append(m.group(1))
        item["file"] = m.group(1)
    # sldIdLst: only the new slides, in plan order
    rels = (u / "ppt/_rels/presentation.xml.rels").read_text(encoding="utf-8")
    rid_of = {}
    for m in re.finditer(r'<Relationship\b[^>]*>', rels):
        el = m.group(0)
        t = re.search(r'Target="(?:/ppt/)?slides/(slide\d+\.xml)"', el)
        if t:
            rid_of[t.group(1)] = re.search(r'\bId="([^"]+)"', el).group(1)
    pres_p = u / "ppt/presentation.xml"
    pres = pres_p.read_text(encoding="utf-8")
    ids = dict(re.findall(r'<p:sldId id="(\d+)" r:id="([^"]+)"/>', pres))
    id_by_rid = {rid: sid for sid, rid in ids.items()}
    entries = []
    for item in plan:
        rid = rid_of[item["file"]]
        sid = id_by_rid[rid]
        item["sld_id"] = sid
        entries.append(f'<p:sldId id="{sid}" r:id="{rid}"/>')
    pres = re.sub(r"<p:sldIdLst>.*?</p:sldIdLst>", "<p:sldIdLst>" + "".join(entries) + "</p:sldIdLst>",
                  pres, flags=re.S)
    # sections, rebuilt from the plan (the master's "Layout examples" section referenced its examples)
    sections: list[tuple[str, list[str]]] = []
    for item in plan:
        if not sections or sections[-1][0] != item["section"]:
            sections.append((item["section"], []))
        sections[-1][1].append(item["sld_id"])
    sec_parts = []
    for i, (name, sids) in enumerate(sections):
        sec_id = str(uuid.uuid5(NS_UUID, f"section:{i}:{name}")).upper()  # index: a name may come back later
        ids_xml = "".join('<p14:sldId id="%s"/>' % s for s in sids)
        sec_parts.append('<p14:section name=%s id="{%s}"><p14:sldIdLst>%s</p14:sldIdLst></p14:section>'
                         % (quoteattr(name), sec_id, ids_xml))
    sec_xml = "".join(sec_parts)
    pres = re.sub(r"(<p14:sectionLst[^>]*>).*?(</p14:sectionLst>)", lambda m: m.group(1) + sec_xml + m.group(2),
                  pres, flags=re.S)
    pres_p.write_text(pres, encoding="utf-8")
    log.extend(remove_webextension(u))
    if (SCRIPTS / "clean.py").exists():
        log.append(_run_script("clean.py", str(u)).strip())
    else:
        from lxml import etree as ET
        rp = u / "ppt/_rels/presentation.xml.rels"
        rels_tree = ET.parse(str(rp))
        for el in list(rels_tree.getroot()):
            if el.get("Type", "").endswith("/slide") and Path(el.get("Target")).name not in new_files:
                rels_tree.getroot().remove(el)
        rels_tree.write(str(rp), xml_declaration=True, encoding="UTF-8")
        log.append("Portable XML duplication; external clean/office validation unavailable")
    out = work / "structure.pptx"
    pack(u, out)
    return out, log


def _duplicate_slide(u: Path, src: str) -> str:
    """Clone a template example without requiring an external skill installation.

    Layout/media relationships remain shared. Notes must be created independently
    by the content builder, so the example's notes relationship is omitted.
    """
    from lxml import etree as ET
    slides = u / "ppt/slides"
    num = max(int(p.stem.removeprefix("slide")) for p in slides.glob("slide*.xml")) + 1
    dst = f"slide{num}.xml"
    shutil.copyfile(slides / src, slides / dst)
    rel = ET.parse(str(slides / "_rels" / (src + ".rels")))
    for child in list(rel.getroot()):
        if child.get("Type", "").endswith("/notesSlide"):
            rel.getroot().remove(child)
    rel.write(str(slides / "_rels" / (dst + ".rels")), xml_declaration=True, encoding="UTF-8")
    rp = u / "ppt/_rels/presentation.xml.rels"
    r = ET.parse(str(rp))
    ids = {el.get("Id") for el in r.getroot()}
    k = 1
    while f"rId{k}" in ids:
        k += 1
    rid = f"rId{k}"
    ET.SubElement(r.getroot(), "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship",
                  Id=rid, Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
                  Target=f"slides/{dst}")
    r.write(str(rp), xml_declaration=True, encoding="UTF-8")
    pp = u / "ppt/presentation.xml"
    pres = ET.parse(str(pp))
    ns = "http://schemas.openxmlformats.org/presentationml/2006/main"
    lst = pres.getroot().find(f"{{{ns}}}sldIdLst")
    sid = max(int(el.get("id")) for el in lst) + 1
    ET.SubElement(lst, f"{{{ns}}}sldId", id=str(sid),
                  attrib={"{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id": rid})
    pres.write(str(pp), xml_declaration=True, encoding="UTF-8")
    cp = u / "[Content_Types].xml"
    ct = ET.parse(str(cp))
    ET.SubElement(ct.getroot(), "{http://schemas.openxmlformats.org/package/2006/content-types}Override",
                  PartName=f"/ppt/slides/{dst}",
                  ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
    ct.write(str(cp), xml_declaration=True, encoding="UTF-8")
    return f"Created ppt/slides/{dst}"
