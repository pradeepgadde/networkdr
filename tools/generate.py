#!/usr/bin/env python3
"""Build the Network Dr static site from a JSON dump of video metadata + transcripts.

Usage: python3 generate.py data.json out_dir
Input JSON: {video_id: {id, title, len, date, desc, kw, tx: [[ts, text], ...]}}
"""
import html, json, re, sys, shutil
from datetime import datetime
from pathlib import Path

CHANNEL = "https://www.youtube.com/@networkdr"
SITE_URL = "https://pradeepgadde.com/networkdr/"


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "video"


def ts_to_sec(ts):
    parts = [int(p) for p in ts.split(":") if p.strip().isdigit()]
    sec = 0
    for p in parts:
        sec = sec * 60 + p
    return sec


def fmt_dur(sec):
    sec = int(sec or 0)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_date(d):
    try:
        return datetime.fromisoformat(d).strftime("%-d %b %Y")
    except Exception:
        return d or ""


def ep_num(title):
    m = re.search(r"\bEP\s*0*(\d+)\b", title or "", re.I)
    return int(m.group(1)) if m else None


def paragraphs(tx):
    """Group caption lines into readable paragraphs, each with a start time."""
    out, cur, start = [], [], None
    for ts, text in tx:
        text = (text or "").strip()
        if not text or text.startswith("[") and text.endswith("]") and len(text) < 20:
            continue
        sec = ts_to_sec(ts) if ts else None
        if start is None:
            start = sec
        cur.append((sec, text))
        joined = " ".join(t for _, t in cur)
        if len(joined) > 420 and re.search(r"[.!?][\"')]?$", text):
            out.append((start, cur))
            cur, start = [], None
    if cur:
        out.append((start, cur))
    return out


def page(title, body, desc, depth, canonical, extra_head=""):
    pre = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta name="color-scheme" content="light dark">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@112,500;125,700;125,800&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{pre}assets/style.css">
<link rel="icon" href="{pre}assets/favicon.svg" type="image/svg+xml">
{extra_head}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="masthead">
  <a class="brand" href="{pre}" aria-label="Network Dr home">
    <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true"><rect x="2" y="9" width="28" height="14" rx="3" fill="none" stroke="currentColor" stroke-width="2"/><rect x="7" y="13" width="5" height="6" rx="1" fill="currentColor"/><rect x="14" y="13" width="5" height="6" rx="1" fill="currentColor"/><circle cx="24.5" cy="16" r="2.2" class="led"/></svg>
    <span>Network Dr</span>
  </a>
  <nav aria-label="Primary">
    <a href="{pre}">Episodes</a>
    <a href="{CHANNEL}" rel="noopener">YouTube</a>
  </nav>
</header>
<main id="main">
{body}
</main>
<footer class="foot">
  <p>Transcripts are YouTube's automatic captions and may contain errors. Videos &copy; Network Dr.</p>
</footer>
</body>
</html>
"""


def build(data_path, out):
    data = json.loads(Path(data_path).read_text())
    out = Path(out)
    here = Path(__file__).parent
    vids = [v for v in data.values() if v and v.get("title")]
    vids.sort(key=lambda v: (v.get("date") or ""), reverse=True)

    slugs = set()
    for v in vids:
        base = slugify(v["title"])
        s, i = base, 2
        while s in slugs:
            s, i = f"{base}-{i}", i + 1
        slugs.add(s)
        v["slug"] = s

    # assets
    (out / "assets").mkdir(parents=True, exist_ok=True)
    for f in (here / "assets").iterdir():
        shutil.copy(f, out / "assets" / f.name)

    # video pages
    for idx, v in enumerate(vids):
        newer = vids[idx - 1] if idx > 0 else None
        older = vids[idx + 1] if idx + 1 < len(vids) else None
        ep = ep_num(v["title"])
        paras = paragraphs(v.get("tx") or [])
        words = sum(len(t.split()) for _, seg in paras for _, t in seg)
        tx_html = []
        for start, seg in paras:
            spans = "".join(
                f'<span data-t="{s}">{html.escape(t)}</span> ' if s is not None else f"<span>{html.escape(t)}</span> "
                for s, t in seg
            )
            stamp = (
                f'<a class="stamp" href="https://www.youtube.com/watch?v={v["id"]}&amp;t={start}s" data-seek="{start}" '
                f'aria-label="Play from {fmt_dur(start)}">{fmt_dur(start)}</a>'
                if start is not None else ""
            )
            tx_html.append(f"<p>{stamp}{spans.strip()}</p>")
        transcript = "\n".join(tx_html) or '<p class="empty">No transcript is available for this video yet.</p>'
        desc = v.get("desc", "").strip()
        summary = " ".join(t for _, seg in paras[:1] for _, t in seg)[:180] or v["title"]
        pager = ""
        if older or newer:
            pager = '<nav class="pager" aria-label="More episodes">'
            pager += (f'<a class="prev" href="../{older["slug"]}/"><small>Previous</small>{html.escape(older["title"])}</a>' if older else "<span></span>")
            pager += (f'<a class="next" href="../{newer["slug"]}/"><small>Next</small>{html.escape(newer["title"])}</a>' if newer else "<span></span>")
            pager += "</nav>"
        body = f"""
<article class="episode">
  <div class="stage">
    <div class="stage-inner">
      <div class="player"><iframe id="yt" src="https://www.youtube-nocookie.com/embed/{v['id']}?enablejsapi=1&amp;rel=0&amp;modestbranding=1" title="{html.escape(v['title'])}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></div>
      <div class="ep-head">
        {f'<span class="ep-no" aria-label="Episode {ep}">{ep}</span>' if ep else ''}
        <div>
          <h1>{html.escape(v['title'])}</h1>
          <p class="meta"><time datetime="{html.escape(v.get('date') or '')}">{fmt_date(v.get('date'))}</time><span>{fmt_dur(v.get('len'))}</span><a href="https://www.youtube.com/watch?v={v['id']}" rel="noopener">Watch on YouTube</a></p>
        </div>
      </div>
      {f'<p class="desc">{html.escape(desc)}</p>' if desc else ''}
      {pager}
    </div>
  </div>
  <section class="transcript" aria-labelledby="tx-h">
    <div class="tx-bar">
      <h2 id="tx-h">Transcript</h2>
      <span class="tx-count">{words:,} words</span>
      <label class="follow"><input type="checkbox" id="follow" checked> Follow along</label>
      <button type="button" id="copy-tx" class="btn">Copy text</button>
    </div>
    <div class="tx-body" id="tx">
{transcript}
    </div>
  </section>
</article>
<script src="../../assets/player.js" defer></script>
"""
        d = out / "videos" / v["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page(f"{v['title']} · Network Dr", body, summary, 2, f"{SITE_URL}videos/{v['slug']}/"))

    # index
    cards = []
    for v in vids:
        ep = ep_num(v["title"])
        cards.append(f"""<li class="card" data-q="{html.escape((v['title'] + ' ' + ' '.join(v.get('kw') or [])).lower())}">
  <a href="videos/{v['slug']}/">
    <span class="thumb"><img src="https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg" alt="" loading="lazy" width="480" height="360"><span class="dur">{fmt_dur(v.get('len'))}</span></span>
    <span class="card-body">
      {f'<span class="port" aria-hidden="true">{ep}</span>' if ep else '<span class="port port-blank" aria-hidden="true"></span>'}
      <span class="card-title">{html.escape(v['title'])}</span>
      <time datetime="{html.escape(v.get('date') or '')}">{fmt_date(v.get('date'))}</time>
    </span>
  </a>
</li>""")
    total = sum(int(v.get("len") or 0) for v in vids)
    body = f"""
<section class="hero">
  <h1>Network Dr</h1>
  <p class="lede">How networks work, and the histories of the companies that build them. Every video, with its full transcript.</p>
  <p class="stats">{len(vids)} episodes, {round(total/3600, 1)} hours of video</p>
</section>
<section class="library" aria-labelledby="lib-h">
  <div class="lib-bar">
    <h2 id="lib-h">All episodes</h2>
    <label class="search"><span class="sr">Search episodes</span><input type="search" id="q" placeholder="Search episodes" autocomplete="off"></label>
  </div>
  <p id="no-results" class="empty" hidden>No episodes match that search.</p>
  <ul class="grid" id="grid">
{chr(10).join(cards)}
  </ul>
</section>
<script src="assets/index.js" defer></script>
"""
    (out / "index.html").write_text(page("Network Dr: every episode with transcripts", body, "Every Network Dr video with its full transcript.", 0, SITE_URL))
    (out / ".nojekyll").write_text("")
    print(f"built {len(vids)} video pages into {out}")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
