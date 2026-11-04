#!/usr/bin/env python3
"""Build the Network Dr static site from a JSON dump of video metadata + transcripts.

Usage: python3 tools/generate.py data/videos.json <out_dir>
  Run from the repo root. Use "." as out_dir to rebuild the repo in place.
Input JSON: {video_id: {id, title, len, date, desc, kw, tx: [[ts, text], ...]}}

Pages produced:
  index.html                 home: banner, latest uploads, start-here route, series shelves
  all/index.html             every video, searchable and filterable by series
  series/<key>/index.html    one page per series, in episode order
  videos/<slug>/index.html   one page per video: wide player, transcript below
"""
import html, json, re, sys, shutil
from datetime import datetime
from pathlib import Path

CHANNEL = "https://www.youtube.com/@networkdr"
SITE_URL = "https://pradeepgadde.com/networkdr/"

# Old series addresses that should keep working: old key -> current key.
RENAMED_SERIES = {"company-histories": "networking-landscape"}

# Series, in the order they appear on the home page. Course parts are ranges of
# the course's episode numbers; the company series uses the EPnn in titles.
SERIES = [
    dict(key="the-big-picture", name="The Big Picture", kind="course", lo=1, hi=8,
         blurb="How networks fit together, from a single packet to cloud and AI fabrics, in eight episodes."),
    dict(key="protocol-deep-dives", name="Protocol Deep Dives", kind="course", lo=9, hi=44,
         blurb="One protocol at a time, from the Ethernet frame up through TCP, DNS, BGP, TLS and beyond, ending in a capstone."),
    dict(key="bonus-episodes", name="Bonus Episodes", kind="course", lo=45, hi=47,
         blurb="Zero trust, 802.1X and MACsec: securing who and what gets onto the network."),
    dict(key="bonus-deep-dives", name="Bonus Deep Dives", kind="course", lo=48, hi=999,
         blurb="Provider and data-center topics in more depth: IS-IS, LDP, RSVP, RPKI, AI clusters, peering, SmartNICs and more."),
    dict(key="networking-landscape", name="Networking Landscape", kind="company", lo=1, hi=999,
         blurb="Who builds the network: a 2026 overview of the industry, then the stories of Cisco, Juniper, Arista, Broadcom, Palo Alto Networks, Zscaler, HPE Aruba and more."),
]


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "video"


def ts_to_sec(ts):
    sec = 0
    for p in [int(p) for p in ts.split(":") if p.strip().isdigit()]:
        sec = sec * 60 + p
    return sec


def fmt_dur(sec):
    sec = int(sec or 0)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_hours(sec):
    h = sec / 3600
    return f"{h:.1f} hours" if h >= 1 else f"{round(sec / 60)} minutes"


def fmt_date(d):
    try:
        return datetime.fromisoformat(d).strftime("%-d %b %Y")
    except Exception:
        return d or ""


def esc(s):
    return html.escape(s or "")


def paragraphs(tx):
    """Group caption lines into readable paragraphs, each with a start time."""
    out, cur, start = [], [], None
    for ts, text in tx:
        text = (text or "").strip()
        if not text or (text.startswith("[") and text.endswith("]") and len(text) < 20):
            continue
        sec = ts_to_sec(ts) if ts else None
        if start is None:
            start = sec
        cur.append((sec, text))
        if len(" ".join(t for _, t in cur)) > 420 and re.search(r"[.!?][\"')]?$", text):
            out.append((start, cur))
            cur, start = [], None
    if cur:
        out.append((start, cur))
    return out


def classify(vids):
    """Give every video a series and an episode number."""
    by_date = sorted(vids, key=lambda v: v.get("date") or "")
    prev, used = 0, set()
    for v in by_date:
        t = v["title"]
        m = re.search(r"\bEP\s*0*(\d+)\b", t, re.I)
        if m or "landscape" in t.lower():
            v["kind"], v["no"] = "company", int(m.group(1)) if m else 1
            continue
        first = " ".join(x for _, x in (v.get("tx") or [])[:2])
        m = re.search(r"\bepisode (\d+)\b", first, re.I)
        n = int(m.group(1)) if m else None
        if n is None or n in used:
            n = prev + 1
        v["kind"], v["no"] = "course", n
        used.add(n)
        prev = n
    for v in vids:
        for s in SERIES:
            if s["kind"] == v["kind"] and s["lo"] <= v["no"] <= s["hi"]:
                v["series"] = s
                break
    for s in SERIES:
        s["vids"] = sorted([v for v in vids if v.get("series") is s], key=lambda v: v["no"])
        s["secs"] = sum(int(v.get("len") or 0) for v in s["vids"])


def ep_label(v):
    return f"Episode {v['no']}" if v["kind"] == "course" else f"EP{v['no']:02d}"


def page(title, body, desc, depth, canonical, nav_here=""):
    pre = "../" * depth
    cur = lambda k: ' aria-current="page"' if k == nav_here else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE_URL}assets/og-image.png">
<meta property="og:image:alt" content="Network Dr street sign over a map of network links">
<meta property="og:site_name" content="Network Dr">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1C2125">
<meta name="color-scheme" content="light dark">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Overpass:ital,wght@0,400;0,600;0,700;0,800;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{pre}assets/style.css">
<link rel="icon" href="{pre}assets/favicon.svg" type="image/svg+xml">
<link rel="icon" href="{pre}assets/icon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="{pre}assets/apple-touch-icon-180.png">
<link rel="manifest" href="{pre}assets/site.webmanifest">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="masthead">
  <a class="brand" href="{pre}" aria-label="Network Dr home"><img src="{pre}assets/logo.svg" alt="" width="44" height="44"><span>Network Dr</span></a>
  <nav aria-label="Primary">
    <a href="{pre}"{cur('home')}>Home</a>
    <a href="{pre}all/"{cur('all')}>All videos</a>
    <a href="{CHANNEL}" rel="noopener">YouTube</a>
  </nav>
</header>
<main id="main">
{body}
</main>
<footer class="foot">
  <a class="foot-mark" href="{CHANNEL}" rel="noopener"><img src="{pre}assets/logo.svg" alt="Network Dr on YouTube" width="40" height="40"></a>
  <p>Transcripts are YouTube's automatic captions and may contain errors. Videos &copy; Network Dr.</p>
</footer>
</body>
</html>
"""


def thumb(v, size="hqdefault"):
    return (f'<span class="thumb"><img src="https://i.ytimg.com/vi/{v["id"]}/{size}.jpg" alt="" loading="lazy" '
            f'width="480" height="360"><span class="dur">{fmt_dur(v.get("len"))}</span></span>')


def card(v, pre, show_series=True):
    q = esc((v["title"] + " " + v["series"]["name"] + " " + " ".join(v.get("kw") or [])).lower())
    sub = f'{esc(v["series"]["name"])}, {ep_label(v).lower() if v["kind"] == "course" else ep_label(v)}' if show_series else fmt_date(v.get("date"))
    return f"""<li class="card" data-q="{q}" data-series="{v['series']['key']}">
  <a href="{pre}videos/{v['slug']}/">
    {thumb(v)}
    <span class="card-body">
      <span class="sign" aria-hidden="true">{v['no']}</span>
      <span class="card-title">{esc(v['title'])}</span>
      <span class="card-sub">{sub}</span>
    </span>
  </a>
</li>"""


def route_row(v, pre):
    return f"""<li><a href="{pre}videos/{v['slug']}/">
  <span class="sign" aria-hidden="true">{v['no']}</span>
  <span class="route-title">{esc(v['title'])}</span>
  <span class="route-dur">{fmt_dur(v.get('len'))}</span>
</a></li>"""


def build(data_path, out):
    data = json.loads(Path(data_path).read_text())
    out = Path(out)
    here = Path(__file__).parent
    vids = [v for v in data.values() if v and v.get("title")]
    vids.sort(key=lambda v: (v.get("date") or ""), reverse=True)
    classify(vids)

    slugs = set()
    for v in vids:
        base = slugify(v["title"])
        s, i = base, 2
        while s in slugs:
            s, i = f"{base}-{i}", i + 1
        slugs.add(s)
        v["slug"] = s

    # Assets live in the repo's assets/ folder (or beside this script during development).
    src = next(p for p in (here / "assets", here.parent / "assets") if p.is_dir())
    (out / "assets").mkdir(parents=True, exist_ok=True)
    if src.resolve() != (out / "assets").resolve():
        for f in src.iterdir():
            shutil.copy(f, out / "assets" / f.name)

    # ---- video pages -------------------------------------------------------
    for v in vids:
        s = v["series"]
        seq = s["vids"]
        i = seq.index(v)
        prev_v = seq[i - 1] if i > 0 else None
        next_v = seq[i + 1] if i + 1 < len(seq) else None
        paras = paragraphs(v.get("tx") or [])
        words = sum(len(t.split()) for _, seg in paras for _, t in seg)
        tx_html = []
        for start, seg in paras:
            spans = "".join(f'<span data-t="{t0}">{esc(t)}</span> ' if t0 is not None else f"<span>{esc(t)}</span> " for t0, t in seg)
            stamp = (f'<a class="stamp" href="https://www.youtube.com/watch?v={v["id"]}&amp;t={start}s" data-seek="{start}" '
                     f'aria-label="Play from {fmt_dur(start)}">{fmt_dur(start)}</a>' if start is not None else "")
            tx_html.append(f"<p>{stamp}{spans.strip()}</p>")
        transcript = "\n".join(tx_html) or '<p class="empty">No transcript is available for this video yet.</p>'
        desc = (v.get("desc") or "").strip()
        summary = " ".join(t for _, seg in paras[:1] for _, t in seg)[:180] or v["title"]
        pager = ""
        if prev_v or next_v:
            pager = '<nav class="pager" aria-label="More in this series">'
            pager += (f'<a class="prev" href="../{prev_v["slug"]}/"><small>Previous: {ep_label(prev_v)}</small>{esc(prev_v["title"])}</a>' if prev_v else "<span></span>")
            pager += (f'<a class="next" href="../{next_v["slug"]}/"><small>Next: {ep_label(next_v)}</small>{esc(next_v["title"])}</a>' if next_v else "<span></span>")
            pager += "</nav>"
        body = f"""
<article class="episode">
  <div class="player"><iframe id="yt" src="https://www.youtube-nocookie.com/embed/{v['id']}?enablejsapi=1&amp;rel=0&amp;modestbranding=1" title="{esc(v['title'])}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></div>
  <header class="ep-head">
    <span class="sign sign-lg" aria-hidden="true">{v['no']}</span>
    <div>
      <p class="crumb"><a href="../../series/{s['key']}/">{esc(s['name'])}</a>, {ep_label(v)}</p>
      <h1>{esc(v['title'])}</h1>
      <p class="meta"><time datetime="{esc(v.get('date'))}">{fmt_date(v.get('date'))}</time><span>{fmt_dur(v.get('len'))}</span><a href="https://www.youtube.com/watch?v={v['id']}" rel="noopener">Watch on YouTube</a></p>
    </div>
  </header>
  {f'<p class="desc">{esc(desc)}</p>' if desc else ''}
  <section class="transcript" aria-labelledby="tx-h">
    <div class="tx-bar">
      <h2 id="tx-h">Transcript</h2>
      <span class="tx-count">{words:,} words</span>
      <label class="follow"><input type="checkbox" id="follow" checked> Follow along</label>
      <button type="button" id="expand-tx" class="btn btn-quiet" aria-controls="tx" aria-expanded="false">Show all</button>
      <button type="button" id="copy-tx" class="btn">Copy text</button>
    </div>
    <div class="tx-body" id="tx" tabindex="0" aria-label="Transcript text">
{transcript}
    </div>
  </section>
  {pager}
</article>
<script src="../../assets/player.js" defer></script>
"""
        d = out / "videos" / v["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page(f"{v['title']} · Network Dr", body, summary, 2, f"{SITE_URL}videos/{v['slug']}/"))

    # ---- series pages ------------------------------------------------------
    for s in SERIES:
        if not s["vids"]:
            continue
        first, last = s["vids"][0], s["vids"][-1]
        rng = f"Episodes {first['no']}–{last['no']}" if s["kind"] == "course" else f"EP{first['no']:02d}–EP{last['no']:02d}"
        body = f"""
<section class="series-head">
  <p class="crumb"><a href="../../">Home</a></p>
  <h1>{esc(s['name'])}</h1>
  <p class="lede">{esc(s['blurb'])}</p>
  <p class="stats">{rng}, {len(s['vids'])} videos, {fmt_hours(s['secs'])}</p>
  <p><a class="btn btn-lg" href="../../videos/{first['slug']}/">Start with {ep_label(first).lower() if s['kind'] == 'course' else ep_label(first)}</a></p>
</section>
<ol class="grid" aria-label="{esc(s['name'])} in order">
{chr(10).join(card(v, '../../', show_series=False) for v in s['vids'])}
</ol>
"""
        d = out / "series" / s["key"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page(f"{s['name']} · Network Dr", body, s["blurb"], 2, f"{SITE_URL}series/{s['key']}/"))

    # ---- redirects for renamed series --------------------------------------
    for old, new in RENAMED_SERIES.items():
        d = out / "series" / old
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Moved · Network Dr</title>
<meta http-equiv="refresh" content="0; url=../{new}/">
<link rel="canonical" href="{SITE_URL}series/{new}/"><meta name="robots" content="noindex"></head>
<body><p>This series moved to <a href="../{new}/">its new page</a>.</p></body></html>
""")

    # ---- all videos --------------------------------------------------------
    chips = "".join(f'<option value="{s["key"]}">{esc(s["name"])} ({len(s["vids"])})</option>' for s in SERIES if s["vids"])
    body = f"""
<section class="series-head">
  <h1>All videos</h1>
  <p class="stats">{len(vids)} videos, {fmt_hours(sum(int(v.get('len') or 0) for v in vids))}, newest first</p>
</section>
<div class="filters">
  <label class="search"><span class="sr">Search videos</span><input type="search" id="q" placeholder="Search by title or topic" autocomplete="off"></label>
  <label class="pick"><span class="sr">Series</span><select id="series"><option value="">All series</option>{chips}</select></label>
  <span id="count" class="stats" aria-live="polite"></span>
</div>
<p id="no-results" class="empty" hidden>No videos match. Try a shorter search or pick All series.</p>
<ul class="grid" id="grid">
{chr(10).join(card(v, '../') for v in vids)}
</ul>
<script src="../assets/index.js" defer></script>
"""
    (out / "all").mkdir(parents=True, exist_ok=True)
    (out / "all" / "index.html").write_text(page("All videos · Network Dr", body, "Every Network Dr video with its full transcript.", 1, f"{SITE_URL}all/", "all"))

    # ---- home --------------------------------------------------------------
    latest, also = vids[0], vids[1:4]
    start = SERIES[0]
    shelves = []
    for s in SERIES[1:]:
        if not s["vids"]:
            continue
        pick = s["vids"][-4:][::-1] if s["kind"] == "company" else s["vids"][:4]
        shelves.append(f"""
<section class="shelf" aria-labelledby="sh-{s['key']}">
  <div class="shelf-head">
    <div>
      <h2 id="sh-{s['key']}">{esc(s['name'])}</h2>
      <p>{esc(s['blurb'])}</p>
    </div>
    <a class="more" href="series/{s['key']}/">All {len(s['vids'])} videos<span class="sr"> in {esc(s['name'])}</span></a>
  </div>
  <ul class="grid grid-4">
{chr(10).join(card(v, '', show_series=False) for v in pick)}
  </ul>
</section>""")
    total = sum(int(v.get("len") or 0) for v in vids)
    lp = paragraphs(latest.get("tx") or [])
    latest_sum = " ".join(t for _, seg in lp[:1] for _, t in seg)
    latest_sum = (latest_sum[:260].rsplit(" ", 1)[0] + "…") if len(latest_sum) > 260 else latest_sum
    body = f"""
<section class="hero">
  <div class="banner"><img src="assets/banner.svg" alt="Network Dr: a green street sign over a map of network links" width="2560" height="1100"></div>
  <h1 class="sr">Network Dr</h1>
  <div class="intro">
    <p class="lede">Where every packet finds its route. Clear explainers on how networks work, and the stories of the companies that build them, each with its full transcript.</p>
    <p class="cta"><a class="btn btn-lg" href="videos/{start['vids'][0]['slug']}/">Start with episode 1</a><a class="more" href="all/">Browse all {len(vids)} videos</a></p>
    <p class="stats">{len(vids)} videos, {fmt_hours(total)}</p>
  </div>
</section>

<section class="latest" aria-labelledby="latest-h">
  <h2 id="latest-h">Latest upload</h2>
  <a class="feature" href="videos/{latest['slug']}/">
    {thumb(latest, 'hqdefault')}
    <span class="feature-body">
      <span class="crumb">{esc(latest['series']['name'])}, {ep_label(latest)}</span>
      <span class="feature-title">{esc(latest['title'])}</span>
      <span class="feature-sum">{esc(latest_sum)}</span>
      <span class="meta"><time datetime="{esc(latest.get('date'))}">{fmt_date(latest.get('date'))}</time><span>{fmt_dur(latest.get('len'))}</span></span>
    </span>
  </a>
  <h3 class="also-h">Also new</h3>
  <ul class="grid grid-3">
{chr(10).join(card(v, '') for v in also)}
  </ul>
</section>

<section class="route" aria-labelledby="route-h">
  <div class="shelf-head">
    <div>
      <h2 id="route-h">Start here: {esc(start['name'])}</h2>
      <p>{esc(start['blurb'])} About {fmt_hours(start['secs'])} in all.</p>
    </div>
    <a class="more" href="series/{start['key']}/">See the series</a>
  </div>
  <ol class="route-list">
{chr(10).join(route_row(v, '') for v in start['vids'])}
  </ol>
</section>
{''.join(shelves)}
"""
    (out / "index.html").write_text(page("Network Dr: networking explained, with transcripts", body, "Clear networking explainers and company histories, each with its full transcript.", 0, SITE_URL, "home"))
    if not (out / ".nojekyll").exists():
        (out / ".nojekyll").write_text("Serve files as-is; no Jekyll processing.\n")
    for s in SERIES:
        print(f"{s['name']}: {len(s['vids'])} -> " + ", ".join(str(v['no']) for v in s['vids']))
    print(f"built {len(vids)} video pages into {out}")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
