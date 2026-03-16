#!/usr/bin/env python3

"""
Fetch the full QRZ DXCC table and distill it into a small JSON mapping.

Usage:
    export QRZ_USERNAME=your_user
    export QRZ_PASSWORD=your_pass
    python fetch_qrz_dxcc_table.py

Output:
    dxcc_table.json
"""

import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


QRZ_XML_BASE = "https://xmldata.qrz.com/xml/current/"


def strip_ns(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def xml_to_dict(elem):
    d = {}
    if elem is None:
        return d
    for child in elem:
        d[strip_ns(child.tag)] = (child.text or "").strip()
    return d


def http_get(params):
    url = QRZ_XML_BASE + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as resp:
        return resp.read()


def login(username, password):
    xml = http_get({
        "username": username,
        "password": password,
    })

    root = ET.fromstring(xml)

    session = None
    for elem in root.iter():
        if strip_ns(elem.tag) == "Session":
            session = xml_to_dict(elem)
            break

    if not session:
        raise RuntimeError("QRZ login failed: no Session block")

    key = session.get("Key") or session.get("key")
    if not key:
        raise RuntimeError("QRZ login failed: no session key returned")

    return key


def fetch_dxcc_table(session_key):
    xml = http_get({
        "s": session_key,
        "dxcc": "all"
    })

    root = ET.fromstring(xml)

    dxcc_records = []

    for elem in root.iter():
        if strip_ns(elem.tag) == "DXCC":
            dxcc_records.append(xml_to_dict(elem))

    return dxcc_records


def build_table(records):
    table = {}

    for r in records:
        dxcc = (r.get("dxcc") or "").strip()
        if not dxcc:
            continue

        continent = (r.get("continent") or "").strip().upper()

        table[dxcc] = {
            "continent": continent,
            "name": r.get("name"),
            "cc": r.get("cc"),
        }

    return table


def main():
    username = os.getenv("QRZ_USERNAME")
    password = os.getenv("QRZ_PASSWORD")

    if not username or not password:
        print("Set QRZ_USERNAME and QRZ_PASSWORD in environment")
        sys.exit(1)

    print("Logging into QRZ...")
    key = login(username, password)

    print("Fetching DXCC table...")
    records = fetch_dxcc_table(key)

    print(f"Received {len(records)} DXCC records")

    table = build_table(records)

    outfile = "dxcc_table.json"

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(table, f, indent=2, sort_keys=True)

    print(f"Wrote {outfile}")
    print(f"{len(table)} DXCC entries")


if __name__ == "__main__":
    main()