import laspy, numpy as np, time, sys, requests
from laspy import CopcReader, Bounds
# count bytes fetched by wrapping requests.Session.get / requests.get
fetched = {'bytes':0,'calls':0}
_orig = requests.Session.request
def _req(self, method, url, *a, **k):
    r = _orig(self, method, url, *a, **k)
    fetched['calls'] += 1; fetched['bytes'] += len(r.content) if method.upper()=='GET' else 0
    return r
requests.Session.request = _req
_origget = requests.get
def _get(url, *a, **k):
    r = _origget(url, *a, **k); fetched['calls'] += 1; fetched['bytes'] += len(r.content); return r
requests.get = _get
for label, url, (x0,y0,x1,y1) in [
  ('AHN4 Utrecht crop C', 'https://basisdata.nl/hwh-ahn/AHN4_KM/01_LAZ/AHN4_C_135000_455000.COPC.LAZ', (135330,455450,135530,455650)),
  ('AHN6 2025 Groningen centre', 'https://basisdata.nl/hwh-ahn/AHN6/01_LAZ/AHN6_2025_C_233000_582000.COPC.LAZ', (233400,582400,233600,582600)),
]:
    fetched.update(bytes=0, calls=0)
    t=time.perf_counter()
    try:
        url2 = requests.head(url, allow_redirects=True, timeout=30).url
        with CopcReader.open(url2) as r:
            h = r.header
            pts = r.query(Bounds(mins=np.array([x0,y0]), maxs=np.array([x1,y1])))
        c = np.asarray(pts.classification); u,n = np.unique(c, return_counts=True)
        area=(x1-x0)*(y1-y0)
        print(f"== {label}\n url={url}\n header: LAS {h.version} PF{h.point_format.id} total_points={h.point_count} scales={h.scales} offsets={h.offsets} software='{h.generating_software}' created={h.creation_date}")
        print(f" bbox {x0},{y0}-{x1},{y1}: {len(pts)} pts ({len(pts)/area:.1f}/m2), first returns {(np.asarray(pts.return_number)==1).sum()/area:.1f}/m2")
        print(" classes:", dict(zip(u.tolist(), n.tolist())))
        print(f" fetched ~{fetched['bytes']/1e6:.1f} MB in {fetched['calls']} HTTP calls, {time.perf_counter()-t:.1f}s")
    except Exception as e:
        import traceback; traceback.print_exc()
