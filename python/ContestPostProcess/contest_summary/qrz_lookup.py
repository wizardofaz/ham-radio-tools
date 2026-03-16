import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


QRZ_XML_BASE = "https://xmldata.qrz.com/xml/current/"


class QRZError(Exception):
    pass


def _safe_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def _norm_upper(value):
    value = _safe_text(value)
    return value.upper() if value else None


def _norm_text(value):
    return _safe_text(value)


QRZ_CALLSIGN_FIELDS = [
    {
        "name": "returned_call",
        "xml_key": "call",
        "normalizer": _norm_upper,
        "freshness_required": True,
    },
    {
        "name": "state",
        "xml_key": "state",
        "normalizer": _norm_text,
        "freshness_required": False,
    },
    {
        "name": "country",
        "xml_key": "country",
        "normalizer": _norm_text,
        "freshness_required": True,
    },
    {
        "name": "dxcc",
        "xml_key": "dxcc",
        "normalizer": _norm_upper,
        "freshness_required": True,
    },
    {
        "name": "continent",
        "xml_key": None,   # filled internally from dxcc lookup
        "normalizer": _norm_upper,
        "freshness_required": True,
    },
    {
        "name": "grid",
        "xml_key": "grid",
        "normalizer": _norm_upper,
        "freshness_required": False,
    },
    {
        "name": "county",
        "xml_key": "county",
        "normalizer": _norm_text,
        "freshness_required": False,
    },
    {
        "name": "fname",
        "xml_key": "fname",
        "normalizer": _norm_text,
        "freshness_required": False,
    },
    {
        "name": "name",
        "xml_key": "name",
        "normalizer": _norm_text,
        "freshness_required": False,
    },
]


def _empty_payload():
    """
    Generate an empty payload matching the QRZ_CALLSIGN_FIELDS schema.
    Ensures failure results have the same structure as successful lookups.
    """
    return {spec["name"]: None for spec in QRZ_CALLSIGN_FIELDS}

def _field_spec_by_name(field_name):
    for spec in QRZ_CALLSIGN_FIELDS:
        if spec["name"] == field_name:
            return spec
    return None


def _has_value(value):
    return _safe_text(value) is not None


def _looks_like_callsign(token):
    """
    Conservative heuristic for picking the 'real' callsign out of slash-separated parts.
    Examples:
        N7DZ/0    -> N7DZ
        KP4/N7DZ  -> N7DZ
        VE3XYZ/P  -> VE3XYZ
    """
    token = _safe_text(token)
    if not token:
        return False

    t = token.upper()

    if not re.search(r"[A-Z]", t):
        return False
    if not re.search(r"\d", t):
        return False

    if len(t) <= 2:
        return False

    if not re.fullmatch(r"[A-Z0-9]+", t):
        return False

    return True


def _strip_ns(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _xml_to_dict(element):
    data = {}
    if element is None:
        return data

    for child in element:
        data[_strip_ns(child.tag)] = _safe_text(child.text)

    return data


def strip_to_base_call(call):
    """
    Pick the most plausible base callsign from a slash call.
    Returns the original call if no better candidate is found.
    """
    call = _safe_text(call)
    if not call:
        return None

    if "/" not in call:
        return call.upper()

    parts = [p.strip().upper() for p in call.split("/") if p.strip()]
    if not parts:
        return call.upper()

    candidates = [p for p in parts if _looks_like_callsign(p)]
    if not candidates:
        return call.upper()

    def score(token):
        letters = len(re.findall(r"[A-Z]", token))
        digits = len(re.findall(r"\d", token))
        return (letters + digits, letters, -digits)

    candidates.sort(key=score, reverse=True)
    return candidates[0]


def cache_ttl_seconds(entry):
    query_call = (entry.get("query_call") or "").upper()
    found = entry.get("found", False)
    lookup_mode = entry.get("lookup_mode")

    if not found:
        return 7 * 86400

    if "/" in query_call:
        return 3 * 86400

    if lookup_mode == "stripped":
        return 30 * 86400

    return 180 * 86400


class QRZLookupClient:
    def __init__(self, cache_path, username=None, password=None, timeout=20):
        self.cache_path = Path(cache_path)
        self.timeout = timeout
        self.username = username or os.getenv("QRZ_USERNAME")
        self.password = password or os.getenv("QRZ_PASSWORD")
        self.session_key = None

        self.cache = self._load_cache()

        self.stats = {
            "qrz_cache_hits": 0,
            "qrz_queries_attempted": 0,
            "qrz_exact_hits": 0,
            "qrz_stripped_hits": 0,
            "qrz_not_found": 0,
            "qrz_login_retries": 0,
            "qrz_dxcc_cache_hits": 0,
            "qrz_dxcc_queries_attempted": 0,
            "qrz_continent_filled": 0,
        }

    def enabled(self):
        return bool(self.username and self.password)

    def _load_cache(self):
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_cache(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2, sort_keys=True)
        tmp.replace(self.cache_path)

    def _http_get_xml(self, params):
        url = QRZ_XML_BASE + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:
            return resp.read()

    def _parse_xml_response(self, xml_bytes):
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as e:
            raise QRZError(f"QRZ returned malformed XML: {e}")

        session = None
        callsign = None
        dxcc = None

        for elem in root.iter():
            tag = _strip_ns(elem.tag)
            if tag == "Session" and session is None:
                session = elem
            elif tag == "Callsign" and callsign is None:
                callsign = elem
            elif tag == "DXCC" and dxcc is None:
                dxcc = elem

        session_data = {k.lower(): v for k, v in _xml_to_dict(session).items()}
        callsign_data = {k.lower(): v for k, v in _xml_to_dict(callsign).items()}
        dxcc_data = {k.lower(): v for k, v in _xml_to_dict(dxcc).items()}

        return session_data, callsign_data, dxcc_data

    def login(self):
        if not self.enabled():
            raise QRZError("QRZ credentials are missing. Set QRZ_USERNAME and QRZ_PASSWORD.")

        xml_bytes = self._http_get_xml({
            "username": self.username,
            "password": self.password,
        })
        session_data, _, _ = self._parse_xml_response(xml_bytes)

        key = session_data.get("key")
        error = session_data.get("error")

        if not key:
            if error:
                raise QRZError(f"QRZ login failed: {error}")
            raise QRZError("QRZ login failed: no session key returned.")

        self.session_key = key
        return key

    def _query_with_session(self, params):
        if not self.session_key:
            self.login()

        time.sleep(1)
        xml_bytes = self._http_get_xml({"s": self.session_key, **params})
        session_data, callsign_data, dxcc_data = self._parse_xml_response(xml_bytes)

        error = session_data.get("error")
        key = session_data.get("key")

        session_error_text = (error or "").lower()
        session_invalid = (not key) or ("session" in session_error_text and not callsign_data and not dxcc_data)

        if session_invalid:
            self.stats["qrz_login_retries"] += 1
            self.login()
            xml_bytes = self._http_get_xml({"s": self.session_key, **params})
            session_data, callsign_data, dxcc_data = self._parse_xml_response(xml_bytes)

        return session_data, callsign_data, dxcc_data

    def _extract_callsign_payload(self, callsign_data):
        payload = {}
        for spec in QRZ_CALLSIGN_FIELDS:
            xml_key = spec["xml_key"]
            if xml_key is None:
                continue
            raw_value = callsign_data.get(xml_key)
            payload[spec["name"]] = spec["normalizer"](raw_value)
        return payload
    
    def _cache_entry_is_fresh(self, entry):
        ts = entry.get("timestamp")
        if not ts:
            return False

        age = time.time() - ts
        if age >= cache_ttl_seconds(entry):
            return False

        if not entry.get("found", False):
            return True

        for spec in QRZ_CALLSIGN_FIELDS:
            if spec["freshness_required"] and not _has_value(entry.get(spec["name"])):
                return False

        return True

    def _dxcc_cache_entry_is_fresh(self, entry):
        ts = entry.get("timestamp")
        if not ts:
            return False

        continent = _norm_upper(entry.get("continent"))
        if not continent:
            return False

        age = time.time() - ts
        return age < (365 * 86400)

    def _lookup_dxcc_continent(self, dxcc):
        dxcc = _norm_upper(dxcc)
        if not dxcc:
            return None

        cache_key = f"DXCC::{dxcc}"
        entry = self.cache.get(cache_key)

        if entry and self._dxcc_cache_entry_is_fresh(entry):
            self.stats["qrz_dxcc_cache_hits"] += 1
            return _norm_upper(entry.get("continent"))

        self.stats["qrz_dxcc_queries_attempted"] += 1

        session_data, _, dxcc_data = self._query_with_session({"dxcc": dxcc})
        error = session_data.get("error")

        if error and not dxcc_data:
            return None

        continent = _norm_upper(dxcc_data.get("continent"))

        self.cache[cache_key] = {
            "dxcc": dxcc,
            "continent": continent,
            "timestamp": int(time.time()),
        }
        self.save_cache()

        return continent

    def _lookup_once(self, query_call):
        self.stats["qrz_queries_attempted"] += 1

        session_data, callsign_data, _ = self._query_with_session({"callsign": query_call})
        error = session_data.get("error")

        if error and "not found" in error.lower():
            payload = _empty_payload()

            return {
                "found": False,
                "query_call": query_call,
                **payload,
                "source": "qrz",
                "lookup_mode": "exact",
                "error": error,
                "timestamp": int(time.time()),
            }

        if error and not callsign_data:
            raise QRZError(f"QRZ lookup failed for {query_call}: {error}")

        payload = self._extract_callsign_payload(callsign_data)
        continent = self._lookup_dxcc_continent(payload.get("dxcc"))
        if continent:
            self.stats["qrz_continent_filled"] += 1

        result = {
            "found": bool(callsign_data),
            "query_call": query_call,
            **payload,
            "continent": continent,
            "source": "qrz",
            "lookup_mode": "exact",
            "error": error,
            "timestamp": int(time.time()),
        }
        return result

    def lookup(self, call):
        """
        Query exact call first.
        If exact call is not found, retry with stripped/base call.
        If exact call *is* found, do not fall back just because fields are incomplete.
        """
        call = _safe_text(call)
        if not call:
            return None

        call = call.upper()

        cache_key = call
        entry = self.cache.get(cache_key)
        if entry and self._cache_entry_is_fresh(entry):
            self.stats["qrz_cache_hits"] += 1
            return entry

        exact = self._lookup_once(call)

        if exact["found"]:
            exact["lookup_mode"] = "exact"
            self.cache[cache_key] = exact
            self.stats["qrz_exact_hits"] += 1
            self.save_cache()
            return exact

        base_call = strip_to_base_call(call)

        if base_call and base_call != call:
            base_cache_key = f"BASE::{base_call}"
            base_entry = self.cache.get(base_cache_key)

            if base_entry and self._cache_entry_is_fresh(base_entry):
                self.stats["qrz_cache_hits"] += 1
                base_result = dict(base_entry)
            else:
                base_result = self._lookup_once(base_call)
                base_result["lookup_mode"] = "stripped"
                self.cache[base_cache_key] = base_result
                self.save_cache()

            if base_result["found"]:
                self.stats["qrz_stripped_hits"] += 1
                aliased = dict(base_result)
                aliased["query_call"] = call
                aliased["lookup_mode"] = "stripped"
                self.cache[cache_key] = aliased
                self.save_cache()
                return aliased

        self.stats["qrz_not_found"] += 1
        self.cache[cache_key] = exact
        self.save_cache()
        return exact


def test_stub():
    """
    Minimal interactive test:
        python -m contest_summary.qrz_lookup N7DZ/0
        python -m contest_summary.qrz_lookup KP4/N7DZ
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m contest_summary.qrz_lookup CALLSIGN")
        print("Requires QRZ_USERNAME and QRZ_PASSWORD in environment.")
        return

    test_call = sys.argv[1]
    cache_file = Path("qrz_cache_test.json")

    client = QRZLookupClient(cache_path=cache_file)

    if not client.enabled():
        print("QRZ credentials not found.")
        print("Set QRZ_USERNAME and QRZ_PASSWORD first.")
        return

    print(f"Lookup: {test_call}")
    print(f"Base-call heuristic: {strip_to_base_call(test_call)}")

    try:
        result = client.lookup(test_call)
    except Exception as e:
        print(f"Lookup failed: {e}")
        return

    print("\nResult:")
    print(json.dumps(result, indent=2, sort_keys=True))

    print("\nStats:")
    print(json.dumps(client.stats, indent=2, sort_keys=True))

    print(f"\nCache file: {cache_file}")


if __name__ == "__main__":
    test_stub()