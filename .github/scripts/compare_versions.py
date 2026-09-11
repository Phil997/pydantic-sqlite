#!/usr/bin/env python3
"""Compares two dot-separated version strings, e.g. "0.6.0" vs "0.5.1".

Prints "true" if the new version is higher than the latest release tag,
"false" otherwise. A missing or empty latest tag always prints "true".

Usage:
    python compare_versions.py NEW_VERSION LATEST_TAG
"""

import re
import sys


def version_key(version):
    return [int(part) for part in re.findall(r"\d+", version)]


def main():
    if len(sys.argv) != 3:
        sys.exit('usage: compare_versions.py <new_version> <latest_tag>')
    new_version, latest_tag = sys.argv[1], sys.argv[2]
    higher = not latest_tag or version_key(new_version) > version_key(latest_tag)
    print("true" if higher else "false")


if __name__ == "__main__":
    main()
