#!/usr/bin/env python3
"""Generates GitHub release notes from auto-generated notes and merged PR bodies.

PR bodies are parsed using the sections from .github/PULL_REQUEST_TEMPLATE.md
and appended to the auto-generated notes.

Usage:
    python generate_release_notes.py VERSION [LAST_TAG] [options]

Environment:
    GITHUB_REPOSITORY   repo as "owner/name" (used unless --repo is given)
    GH_TOKEN            GitHub token for authenticated API requests
    RUNNER_TEMP         output directory (used unless --out is given)
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

API_URL = "https://api.github.com"
TEMPLATE_SECTIONS = ["Breaking Changes", "Features/Fixes", "Misc"]
PLACEHOLDERS = {"", "...", "*", "-", "None"}


def api_request(url, method="GET", token="", data=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        sys.exit(f"GitHub API returned {error.code} for {url}: {error.read().decode()}")


def generate_notes(owner, repo, version, token):
    payload = {"tag_name": version, "target_commitish": "main"}
    result = api_request(f"{API_URL}/repos/{owner}/{repo}/releases/generate-notes",
                         method="POST", token=token, data=payload)
    return result.get("body", "")


def latest_release_date(owner, repo, token):
    try:
        release = api_request(f"{API_URL}/repos/{owner}/{repo}/releases/latest", token=token)
    except SystemExit:
        return None
    return release.get("published_at")


def merged_prs(owner, repo, token):
    prs = []
    page = 1
    while True:
        url = f"{API_URL}/repos/{owner}/{repo}/pulls?state=closed&base=main&per_page=100&page={page}"
        batch = api_request(url, token=token)
        prs.extend(pr for pr in batch if pr.get("merged_at"))
        if len(batch) < 100:
            break
        page += 1
    return prs


def parse_sections(prs, since):
    sections = {name: [] for name in TEMPLATE_SECTIONS}
    for pr in prs:
        if since and (pr.get("merged_at") or "") < since:
            continue
        body = pr.get("body")
        if not body:
            continue
        for name in TEMPLATE_SECTIONS:
            match = re.search(rf"###\s*{re.escape(name)}[:\s]*(.*?)(?=###|\Z)",
                              body, re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            for line in match.group(1).splitlines():
                line = re.sub(r"^\d+[.)]\s*", "", line.strip())
                line = re.sub(r"^[*\-]\s+", "", line).strip()
                if line and line not in PLACEHOLDERS:
                    sections[name].append(f"{line} (#{pr['number']})")
    return sections


def main():
    parser = argparse.ArgumentParser(description="Build GitHub release notes from merged PRs")
    parser.add_argument("version", help="version to release, e.g. 0.6.0")
    parser.add_argument("last_tag", nargs="?", default="", help="previous release tag, e.g. 0.5.1")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""),
                        help='repository as "owner/repo"')
    parser.add_argument("--prs-file", help="read merged PRs from a JSON file instead of the API (testing)")
    parser.add_argument("--since", help="only consider PRs merged at or after this ISO date (testing)")
    parser.add_argument("--out", default=os.path.join(os.environ.get("RUNNER_TEMP", "."), "release_notes.md"))
    parser.add_argument("--no-generate-notes", action="store_true", help="skip the auto-generated notes section")
    args = parser.parse_args()

    token = os.environ.get("GH_TOKEN", "")

    body = ""
    prs = []
    since = args.since

    if args.prs_file:
        with open(args.prs_file, encoding="utf-8") as f:
            prs = json.load(f)
    else:
        if "/" not in args.repo:
            sys.exit("--repo (or GITHUB_REPOSITORY) is required")
        owner, repo = args.repo.split("/", 1)
        if not args.no_generate_notes:
            body = generate_notes(owner, repo, args.version, token)
        if since is None and args.last_tag:
            since = latest_release_date(owner, repo, token)
        prs = merged_prs(owner, repo, token)

    sections = parse_sections(prs, since)

    if body.strip():
        body = body.strip() + "\n"
    if any(sections.values()):
        if body.strip():
            body += "\n"
        body += "---\n\n"
        for name, items in sections.items():
            if items:
                body += f"## {name}\n\n"
                body += "".join(f"- {item}\n" for item in items)
                body += "\n"

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"Release notes written to {args.out}")


if __name__ == "__main__":
    main()
