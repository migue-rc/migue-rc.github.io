#!/usr/bin/env python3
"""Ping IndexNow with recently changed URLs after a publish.

Runs as the last step of `make publish` (also available as `make indexnow`).
IndexNow instantly notifies Bing, Naver, Seznam and Yandex, which share
submissions with other participating engines - and those indexes feed the
retrieval layers of AI search products, so this covers "LLM discoverability"
too.

How it works:
1. The ownership key is auto-discovered: the `<key>.txt` file in the repo
   root whose content equals its own name (served at the site root, which is
   how IndexNow verifies we own the host). IndexNow keys are public by
   design - no secret needed.
2. The sitemap list comes from the Sitemap: lines of robots.txt, which
   gen_discoverability.py keeps in sync with projects.yml.
3. Each live sitemap is fetched; URLs with a <lastmod> within --since-days
   (default 1) are collected and submitted in one batch POST.

Network failures never break the publish: the script warns and exits 0.

Usage:
    python3 scripts/submit_indexnow.py [--since-days N] [--dry-run]
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "migue-rc.github.io"
ENDPOINT = "https://api.indexnow.org/indexnow"


def find_key() -> str:
    for path in ROOT.glob("*.txt"):
        stem = path.stem
        if re.fullmatch(r"[0-9a-f]{32}", stem) and path.read_text().strip() == stem:
            return stem
    sys.exit("ERROR: IndexNow key file not found in repo root "
             "(expected <32-hex-key>.txt containing its own name).")


def sitemap_urls() -> list[str]:
    robots = (ROOT / "robots.txt").read_text()
    return re.findall(r"^Sitemap:\s*(\S+)", robots, re.M)


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def changed_urls(sitemap_xml: str, cutoff: datetime) -> list[str]:
    urls = []
    for entry in re.findall(r"<url>(.*?)</url>", sitemap_xml, re.S):
        loc = re.search(r"<loc>(.*?)</loc>", entry)
        lastmod = re.search(r"<lastmod>(.*?)</lastmod>", entry)
        if not loc:
            continue
        if lastmod:
            try:
                modified = datetime.fromisoformat(lastmod.group(1).replace("Z", "+00:00"))
            except ValueError:
                modified = None
            if modified is not None and modified < cutoff:
                continue
        urls.append(loc.group(1).strip())
    return urls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since-days", type=int, default=1,
                        help="submit URLs modified within this many days (default 1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would be submitted without submitting")
    args = parser.parse_args()

    key = find_key()
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.since_days)

    batch: list[str] = []
    for sitemap in sitemap_urls():
        try:
            xml = fetch(sitemap)
        except Exception as error:  # noqa: BLE001 - never break the publish
            print(f"indexnow: WARNING could not fetch {sitemap}: {error}")
            continue
        fresh = changed_urls(xml, cutoff)
        print(f"indexnow: {sitemap} -> {len(fresh)} changed URL(s)")
        batch.extend(fresh)

    batch = sorted(set(batch))
    if not batch:
        print("indexnow: nothing changed in the window, nothing to submit")
        return
    if args.dry_run:
        print("indexnow: DRY RUN, would submit:")
        for url in batch:
            print(f"  {url}")
        return

    payload = json.dumps({
        "host": HOST,
        "key": key,
        "keyLocation": f"https://{HOST}/{key}.txt",
        "urlList": batch,
    }).encode()
    request = urllib.request.Request(
        ENDPOINT, data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"indexnow: submitted {len(batch)} URL(s), HTTP {response.status}")
    except urllib.error.HTTPError as error:
        print(f"indexnow: WARNING submission rejected: HTTP {error.code} {error.read().decode()[:200]}")
    except Exception as error:  # noqa: BLE001
        print(f"indexnow: WARNING submission failed: {error}")


if __name__ == "__main__":
    main()
