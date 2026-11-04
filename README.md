# Network Dr

Every video from the [Network Dr YouTube channel](https://www.youtube.com/@networkdr), each on its own page with the video embedded and the full transcript below it.

Live site: https://pradeepgadde.com/networkdr/

- `index.html`: home page with the latest upload, the Big Picture course as a starting route, and a shelf per series.
- `all/`: every video, searchable and filterable by series.
- `series/<name>/`: one page per series, in episode order.
- `videos/<slug>/`: one page per video. Click any timestamp or line in the transcript to jump the player there; "Follow along" highlights the line being spoken.
- `assets/`: stylesheet, scripts, logo (`logo.svg`), banner and icons. To change the logo, replace `assets/logo.svg`.
- `tools/generate.py`: rebuilds the site from a JSON export of video metadata and transcripts.

Transcripts come from YouTube's automatic captions and may contain errors. The site is plain static HTML served by GitHub Pages from the `main` branch.
