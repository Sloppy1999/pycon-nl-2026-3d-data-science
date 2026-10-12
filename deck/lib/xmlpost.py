"""Raw OOXML that python-pptx has no API for: transitions (Morph / fade), the on-click build,
language tags, hidden slides, unique slide creation ids, document properties, the fonts and theme of the
embedded chart workbooks, and the reading order of each slide's shapes."""

from __future__ import annotations

import datetime as dt
import re
import uuid
import zipfile
from pathlib import Path

from lxml import etree
from pptx.oxml.ns import qn

MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
P159 = "http://schemas.microsoft.com/office/powerpoint/2015/09/main"
LANG = "en-GB"
NS_UUID = uuid.UUID("6f1c2a43-3d5e-4a8e-9b7c-20261015abcd")

# Morph (PowerPoint 2019 / Microsoft 365) with a fade fallback for older readers.
MORPH_XML = f'''<mc:AlternateContent xmlns:mc="{MC}" xmlns:p="{P}">
  <mc:Choice xmlns:p159="{P159}" Requires="p159">
    <p:transition spd="slow"><p159:morph option="byObject"/></p:transition>
  </mc:Choice>
  <mc:Fallback>
    <p:transition spd="slow"><p:fade/></p:transition>
  </mc:Fallback>
</mc:AlternateContent>'''

FADE_XML = f'''<mc:AlternateContent xmlns:mc="{MC}" xmlns:p="{P}">
  <mc:Choice xmlns:p14="{P14}" Requires="p14">
    <p:transition spd="med" p14:dur="700"><p:fade/></p:transition>
  </mc:Choice>
  <mc:Fallback>
    <p:transition spd="med"><p:fade/></p:transition>
  </mc:Fallback>
</mc:AlternateContent>'''


def set_transition(slide, kind: str):
    sld = slide._element
    for old in sld.findall(qn("p:transition")) + sld.findall(f"{{{MC}}}AlternateContent"):
        sld.remove(old)
    el = etree.fromstring(MORPH_XML if kind == "morph" else FADE_XML)
    anchor = sld.find(qn("p:clrMapOvr"))
    if anchor is None:
        anchor = sld.find(qn("p:cSld"))
    anchor.addnext(el)


def add_click_appear(slide, shape):
    """One on-click 'Appear' entrance for `shape` (the slide 17 hero). Nothing else animates."""
    sld = slide._element
    for old in sld.findall(qn("p:timing")):
        sld.remove(old)
    spid = shape.shape_id
    xml = f'''<p:timing xmlns:p="{P}"><p:tnLst><p:par>
<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>
<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>
<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>
<p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>
<p:par><p:cTn id="5" presetID="1" presetClass="entr" presetSubtype="0" fill="hold" grpId="0" nodeType="clickEffect">
<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>
<p:set><p:cBhvr><p:cTn id="6" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>
<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>
</p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>
</p:childTnLst></p:cTn></p:par>
</p:childTnLst></p:cTn></p:par>
</p:childTnLst></p:cTn></p:par>
</p:childTnLst></p:cTn>
<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>
<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>
</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>
<p:bldLst><p:bldP spid="{spid}" grpId="0"/></p:bldLst></p:timing>'''
    el = etree.fromstring(re.sub(r">\s+<", "><", xml))
    # order: cSld, clrMapOvr, transition (AlternateContent), timing, extLst
    ext = sld.find(qn("p:extLst"))
    if ext is not None:
        ext.addprevious(el)
    else:
        sld.append(el)


def hide(slide):
    slide._element.set("show", "0")


def normalise_lang(root) -> int:
    """All a:rPr / a:endParaRPr / a:defRPr to en-GB; drop spelling-error flags."""
    n = 0
    for tag in ("rPr", "endParaRPr", "defRPr"):
        for el in root.iter(f"{{{A}}}{tag}"):
            if tag != "defRPr" or "lang" in el.attrib:
                el.set("lang", LANG)
                n += 1
            if "err" in el.attrib:
                del el.attrib["err"]
            if "altLang" in el.attrib:
                del el.attrib["altLang"]
    return n


def unique_creation_id(slide, key: str):
    for ext in slide._element.iter(f"{{{P14}}}creationId"):
        ext.set("val", str(uuid.uuid5(NS_UUID, "slide:" + key).int % 4294967295))


def _stable_xlsx(data: bytes, stamp: str, *, theme: bytes | None = None, font: str | None = None) -> bytes:
    """An embedded chart workbook with the deck's timestamp in its core properties and fixed zip entry times, so
    the same inputs give the same bytes. XlsxWriter writes its own defaults into the workbook (Calibri in
    xl/styles.xml, the Office 2007 theme with Calibri, Cambria and its colours in xl/theme/theme1.xml), which show
    in PowerPoint under "Edit data": the cell font becomes `font` and the theme part becomes the deck's own theme
    (`theme`, ppt/theme/theme1.xml: the PyCon NL 2026 colours and Fira Sans)."""
    import io
    src = zipfile.ZipFile(io.BytesIO(data))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out:
        for info in src.infolist():
            body = src.read(info.filename)
            if info.filename == "docProps/core.xml":
                body = re.sub(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*(</dcterms:)",
                              lambda m: m.group(1) + stamp.encode() + m.group(2), body)
            elif info.filename == "xl/styles.xml" and font:
                body = re.sub(rb'<name val="[^"]*"/>', b'<name val="' + font.encode() + b'"/>', body)
            elif info.filename.startswith("xl/theme/") and info.filename.endswith(".xml") and theme:
                body = theme
            zi = zipfile.ZipInfo(info.filename, (1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            out.writestr(zi, body)
    return buf.getvalue()


def finalise_package(pptx_path: Path, *, author: str, title: str, n_slides: int, n_hidden: int,
                     n_notes: int, modified: dt.datetime, workbook_font: str | None = None) -> None:
    """Rewrite docProps/app.xml (slide counts; no company field, no titles of parts) and docProps/core.xml
    (title from content.yaml, author, en-GB), and make the zip deterministic (fixed entry timestamps, sorted
    entries). Embedded chart workbooks get the deck's theme and `workbook_font` (see _stable_xlsx)."""
    from xml.sax.saxutils import escape
    author, title = escape(author), escape(title)
    with zipfile.ZipFile(pptx_path) as zf:
        items = {i.filename: zf.read(i.filename) for i in zf.infolist()}
    app = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><TotalTime>0</TotalTime><Application>Microsoft Office PowerPoint</Application><PresentationFormat>Widescreen</PresentationFormat><Slides>{n_slides}</Slides><Notes>{n_notes}</Notes><HiddenSlides>{n_hidden}</HiddenSlides><MMClips>0</MMClips><ScaleCrop>false</ScaleCrop><LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged><AppVersion>16.0000</AppVersion></Properties>'''
    items["docProps/app.xml"] = app.encode("utf-8")
    stamp = modified.strftime("%Y-%m-%dT%H:%M:%SZ")
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{title}</dc:title><dc:creator>{author}</dc:creator><cp:lastModifiedBy>{author}</cp:lastModifiedBy><dc:language>{LANG}</dc:language><cp:revision>1</cp:revision><dcterms:created xsi:type="dcterms:W3CDTF">{stamp}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{stamp}</dcterms:modified></cp:coreProperties>'''
    items["docProps/core.xml"] = core.encode("utf-8")
    theme = items.get("ppt/theme/theme1.xml")
    for n in list(items):                    # chart workbooks: xlsxwriter stamps the build time into them
        if n.startswith("ppt/embeddings/") and n.endswith(".xlsx"):
            items[n] = _stable_xlsx(items[n], stamp, theme=theme, font=workbook_font)
    names = sorted(items, key=lambda n: (n != "[Content_Types].xml", n))
    tmp = pptx_path.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for n in names:
            info = zipfile.ZipInfo(n, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, items[n])
    tmp.replace(pptx_path)


# Reading order (screen readers follow the spTree order): title, the visual (picture, chart, diagram, code, chips),
# hero, support line, small print / source / conditions, footer, slide number. A stable sort, so the z-order inside
# each group stays as drawn (key-line bars behind their code, chips above their render).
_SMALL_NAMES = ("Source", "!!src", "!!small", "Small print", "Conditions", "Placeholder note")


def _reading_rank(el) -> int:
    ph = el.find(f".//{{{P}}}nvPr/{{{P}}}ph")
    typ = ph.get("type") if ph is not None else None
    if typ in ("title", "ctrTitle"):
        return 0
    if typ == "ftr":
        return 5
    if typ == "sldNum":
        return 6
    cnv = next((c for c in el.iter(f"{{{P}}}cNvPr")), None)
    name = (cnv.get("name") if cnv is not None else "") or ""
    if name.startswith("Hero"):
        return 2
    if name in ("Support", "!!support"):
        return 3
    if name.startswith(_SMALL_NAMES):
        return 4
    return 1


def reading_order(slide) -> list[str]:
    """Reorder the slide's top-level shapes into reading order; returns the names in the new order."""
    tree = slide.shapes._spTree
    shapes = [el for el in tree if el.tag.split("}")[1] in ("sp", "pic", "graphicFrame", "grpSp", "cxnSp",
                                                             "contentPart")]
    if not shapes:
        return []
    ranked = sorted(enumerate(shapes), key=lambda t: (_reading_rank(t[1]), t[0]))
    anchor = shapes[0].getprevious()           # p:grpSpPr
    for el in shapes:
        tree.remove(el)
    for _, el in reversed(ranked):
        anchor.addnext(el)
    out = []
    for _, el in ranked:
        cnv = next((c for c in el.iter(f"{{{P}}}cNvPr")), None)
        out.append((cnv.get("name") if cnv is not None else "") or "")
    return out
