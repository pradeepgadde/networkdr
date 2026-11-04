#!/usr/bin/env python3
"""Merge newly scraped videos into data/videos.json.

Usage: python3 tools/add_videos.py new.json [data/videos.json]
new.json has the same shape as data/videos.json: {video_id: {id, title, len, date, desc, kw, tx}}.
Entries without a title or with an empty transcript are skipped and reported.
"""
import json, sys
from pathlib import Path

new_path = Path(sys.argv[1])
data_path = Path(sys.argv[2] if len(sys.argv) > 2 else "data/videos.json")
data = json.loads(data_path.read_text()) if data_path.exists() else {}
new = json.loads(new_path.read_text())
added, updated, skipped = [], [], []
keep = ("id", "title", "len", "date", "desc", "kw", "tx")
for vid, v in new.items():
    if not v or not v.get("title") or not v.get("tx"):
        skipped.append(vid)
        continue
    v = {k: v.get(k) for k in keep}
    (updated if vid in data else added).append(f"{vid}  {v['title']}")
    data[vid] = v
data_path.parent.mkdir(parents=True, exist_ok=True)
data_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
print(f"total videos: {len(data)}")
for label, items in (("added", added), ("updated", updated), ("skipped (no title or transcript)", skipped)):
    print(f"{label}: {len(items)}")
    for i in items:
        print("  " + i)
