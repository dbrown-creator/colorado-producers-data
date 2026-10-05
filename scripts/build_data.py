#!/usr/bin/env python3
"""Export the Colorado producers data set for this site.

Reads the compiled data set from a checkout of the colorado-farm-trail repo
(source-data/phase2/co_farmers_markets_all_raw.csv, built by its scripts/scrape
pipeline) and writes:

  data/producers.json   records for the map and table
  data/summary.json     counts by category, county and source, plus source growth
  data/producers.csv    the same records as a spreadsheet download

Usage:  python scripts/build_data.py --inputs ../colorado-farm-trail
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SOURCES = {  # source key -> (display name, date it joined the data set)
    "colorado_proud_farm_fresh": ("Colorado Proud Farm Fresh Directory", "2026-07-10"),
    "colorado_proud": ("Colorado Proud farmers market map", "2026-07-20"),
    "cfma": ("Colorado Farmers Market Association", "2026-07-20"),
    "usda": ("USDA local food directories", "2026-10-03"),
    "chaffee_provides": ("Chaffee Provides", "2026-10-03"),
    "curated": ("Farmers market vendor lists", "2026-10-04"),
    "colorado_proud_finder": ("Colorado Proud member directory", "2026-10-04"),
}
VERIFY = {"official-site": "Checked against own website"}
# Order the sources joined; each step of the growth chart adds the producers first
# found in that source.
ORDER = list(SOURCES)


def split_list(s):
    return [p.strip() for p in (s or "").split(",") if p.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, help="path to a colorado-farm-trail checkout")
    args = ap.parse_args()
    inputs = os.path.abspath(args.inputs)
    sys.path.insert(0, os.path.join(inputs, "scripts"))
    from scrape import categories  # noqa: E402
    from build_map_data import social_url, website_url  # noqa: E402
    from scrape.normalize import in_colorado  # noqa: E402

    group_label = {k: label for k, label, _, _ in categories.GROUPS}
    raw = list(csv.DictReader(open(os.path.join(inputs, "source-data", "phase2",
                                                "co_farmers_markets_all_raw.csv"), encoding="utf-8-sig")))
    records = []
    for r in raw:
        src = set(r["Source"].split("+"))
        labels = split_list(r["Category"])
        groups = categories.groups_for(r["Category"])
        lat = r.get("Latitude")
        if lat and not in_colorado(float(lat), float(r["Longitude"])):
            lat = ""  # bad geocode outside Colorado: list it, but don't pin it
        records.append({
            "name": r["Business Name"],
            "groups": [group_label[g] for g in groups],
            "labels": [l for l in labels if l not in categories.BADGES],
            "schools": "Sells to Schools" in labels,
            "address": r["Address"], "city": r["City"], "county": r["County"], "zip": r["Zip"],
            "phone": r["Phone"], "email": r["Email"],
            "website": website_url(r["Website"]) or "",
            "facebook": social_url(r["Facebook"], "https://facebook.com/") or "",
            "instagram": social_url(r["Instagram"], "https://instagram.com/") or "",
            "hours": r["Hours"], "months": r["Months Open"], "products": r["Products"],
            "snap": r["SNAP"] == "Yes", "organic": r["Certified Organic"] == "Yes",
            "lat": round(float(lat), 6) if lat else None,
            "lng": round(float(r["Longitude"]), 6) if lat else None,
            "sources": [SOURCES[s][0] for s in ORDER if s in src],
            "verified": "official-site" in src,
        })
    records.sort(key=lambda m: m["name"].lower())

    # Growth: producers first found in each source, in the order sources joined.
    growth, seen = [], 0
    for i, key in enumerate(ORDER):
        total = sum(1 for r in raw if set(r["Source"].split("+")) & set(ORDER[:i + 1]))
        growth.append({"source": SOURCES[key][0], "date": SOURCES[key][1],
                       "added": total - seen, "total": total})
        seen = total
    growth = [g for g in growth if g["added"]]  # a source that only enriched existing records

    by_group = collections.Counter(g for m in records for g in m["groups"])
    by_county = collections.Counter(m["county"] or "Not set" for m in records)
    by_source = collections.Counter(s for m in records for s in m["sources"])
    n = len(records)
    summary = {
        "generated": dt.date.today().isoformat(),
        "total": n,
        "mapped": sum(1 for m in records if m["lat"] is not None),
        "counties": len([c for c in by_county if c != "Not set"]),
        "sources": len(SOURCES),
        "verified": sum(1 for m in records if m["verified"]),
        "groups": [{"name": label, "count": by_group.get(label, 0)} for _, label, _, _ in categories.GROUPS],
        "counties_list": sorted(({"name": k, "count": v} for k, v in by_county.items()),
                                key=lambda x: (-x["count"], x["name"])),
        "by_source": [{"name": SOURCES[k][0], "count": by_source.get(SOURCES[k][0], 0)} for k in ORDER],
        "growth": growth,
        "completeness": [{"name": f, "count": sum(1 for m in records if m[k])} for f, k in
                         [("Website", "website"), ("Phone", "phone"), ("Email", "email"),
                          ("Facebook or Instagram", "facebook"), ("Hours", "hours"), ("Products", "products")]],
    }
    # Facebook or Instagram: count either.
    summary["completeness"][3]["count"] = sum(1 for m in records if m["facebook"] or m["instagram"])

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "producers.json"), "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(ROOT, "data", "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    cols = ["name", "groups", "labels", "address", "city", "county", "zip", "phone", "email", "website",
            "facebook", "instagram", "hours", "months", "products", "snap", "organic", "lat", "lng", "sources"]
    with open(os.path.join(ROOT, "data", "producers.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([c.replace("groups", "category").replace("labels", "detailed categories") for c in cols])
        for m in records:
            w.writerow(["; ".join(m[c]) if isinstance(m[c], list) else
                        ("Yes" if m[c] is True else ("" if m[c] in (False, None) else m[c])) for c in cols])
    print(f"{n} producers ({summary['mapped']} mapped, {summary['counties']} counties); growth:",
          [(g['source'], g['total']) for g in growth])


if __name__ == "__main__":
    main()
