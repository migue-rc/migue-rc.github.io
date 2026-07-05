#!/usr/bin/env python3
"""Regenerate the auto-maintained blocks of robots.txt and llms.txt.

Source of truth: projects.yml. Every project card whose path lives under the
hub host gets a Sitemap: line in robots.txt and an entry in the Projects
section of llms.txt. Everything outside the BEGIN/END markers is hand-written
and never touched, so the files stay editable.

Run via `make discoverability` (also runs automatically as part of
`make publish`).
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
HOST = "https://migue-rc.github.io"

ROBOTS_BEGIN = "# BEGIN AUTO-SITEMAPS (generated from projects.yml -- run `make discoverability`)"
ROBOTS_END = "# END AUTO-SITEMAPS"
LLMS_BEGIN = "<!-- BEGIN AUTO-PROJECTS (generated from projects.yml -- run `make discoverability`) -->"
LLMS_END = "<!-- END AUTO-PROJECTS -->"


def replace_block(text: str, begin: str, end: str, body: str, filename: str) -> str:
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        sys.exit(f"ERROR: markers not found in {filename}. "
                 f"Expected a block delimited by:\n  {begin}\n  {end}")
    return pattern.sub(begin + "\n" + body + "\n" + end, text)


def main() -> None:
    print("==> Reading projects.yml")
    projects = yaml.safe_load((ROOT / "projects.yml").read_text())
    projects = [p for p in projects if str(p.get("path", "")).startswith(HOST)]
    projects.sort(key=lambda p: p.get("order", 999))
    print(f"    {len(projects)} project card(s) on this host")

    # robots.txt: hub sitemap first, then one line per project site.
    sitemap_lines = [f"Sitemap: {HOST}/sitemap.xml"]
    for p in projects:
        sitemap_lines.append(f"Sitemap: {p['path'].rstrip('/')}/sitemap.xml")

    print("==> Updating robots.txt")
    robots_path = ROOT / "robots.txt"
    robots_path.write_text(replace_block(
        robots_path.read_text(), ROBOTS_BEGIN, ROBOTS_END,
        "\n".join(sitemap_lines), "robots.txt"))
    for line in sitemap_lines:
        print(f"    {line}")

    # llms.txt: one entry per project card.
    llms_lines = []
    for p in projects:
        description = str(p.get("description", "")).strip().rstrip(".")
        llms_lines.append(f"- [{p['title']}]({p['path'].rstrip('/')}/): {description}")

    print("==> Updating llms.txt")
    llms_path = ROOT / "llms.txt"
    llms_path.write_text(replace_block(
        llms_path.read_text(), LLMS_BEGIN, LLMS_END,
        "\n".join(llms_lines), "llms.txt"))
    for p in projects:
        print(f"    - {p['title']}")

    print(f"==> Done: {len(sitemap_lines)} sitemap(s) in robots.txt, "
          f"{len(llms_lines)} project entr(ies) in llms.txt")


if __name__ == "__main__":
    main()
