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

    # Must have at least one letter and one digit
    if not re.search(r"[A-Z]", t):
        return False
    if not re.search(r"\d", t):
        return False

    # Portable designators like P, M, MM, AM, 0, 7 should not win
    if len(t) <= 2:
        return False

    # Basic allowed chars
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

    # Prefer the most callsign-looking token:
    # 1) contains letters+digits
    # 2) longer beats tiny portable suffixes
    # 3) ties broken by more letters
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
        }

    def _cache_ttl_seconds(self, entry):
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

    def _cache_entry_is_fresh(self, entry):
        ts = entry.get("timestamp")
        if not ts:
            return False

        age = time.time() - ts
        return age < self._cache_ttl_seconds(entry)

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

    def _cache_ttl_seconds(self, entry):
        query_call = (entry.get("query_call") or "").upper()
        found = entry.get("found", False)
        lookup_mode = entry.get("lookup_mode")

        # Not found: retry fairly soon
        if not found:
            return 7 * 86400

        # Portable or prefixed/suffixed calls: refresh often
        if "/" in query_call:
            return 3 * 86400

        # Base-call fallback result: medium lifetime
        if lookup_mode == "stripped":
            return 30 * 86400

        # Ordinary exact calls: long lifetime
        return 180 * 86400


    def _cache_entry_is_fresh(self, entry):
        ts = entry.get("timestamp")
        if not ts:
            return False

        age = time.time() - ts
        return age < self._cache_ttl_seconds(entry)

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

        for elem in root.iter():
            tag = _strip_ns(elem.tag)
            if tag == "Session" and session is None:
                session = elem
            elif tag == "Callsign" and callsign is None:
                callsign = elem

        session_data = _xml_to_dict(session)
        callsign_data = {k.lower(): v for k, v in _xml_to_dict(callsign).items()}

        return session_data, callsign_data

    def login(self):
        if not self.enabled():
            raise QRZError("QRZ credentials are missing. Set QRZ_USERNAME and QRZ_PASSWORD.")

        xml_bytes = self._http_get_xml({
            "username": self.username,
            "password": self.password,
        })
        session_data, _ = self._parse_xml_response(xml_bytes)

        key = session_data.get("Key") or session_data.get("key")
        error = session_data.get("Error") or session_data.get("error")

        if not key:
            if error:
                raise QRZError(f"QRZ login failed: {error}")
            raise QRZError("QRZ login failed: no session key returned.")

        self.session_key = key
        return key

    def _lookup_once(self, query_call):
        if not self.session_key:
            self.login()

        self.stats["qrz_queries_attempted"] += 1

        time.sleep(1)
        xml_bytes = self._http_get_xml({
            "s": self.session_key,
            "callsign": query_call,
        })
        session_data, callsign_data = self._parse_xml_response(xml_bytes)

        error = session_data.get("Error") or session_data.get("error")
        key = session_data.get("Key") or session_data.get("key")

        # Session invalid/expired: QRZ docs say re-login and retry. :contentReference[oaicite:1]{index=1}
        session_error_text = (error or "").lower() if error else ""
        if (not key) or ("session" in session_error_text and "error" not in callsign_data):
            self.stats["qrz_login_retries"] += 1
            self.login()
            xml_bytes = self._http_get_xml({
                "s": self.session_key,
                "callsign": query_call,
            })
            session_data, callsign_data = self._parse_xml_response(xml_bytes)
            error = session_data.get("Error") or session_data.get("error")

        if error and "not found" in error.lower():
            return {
                "found": False,
                "query_call": query_call,
                "returned_call": None,
                "state": None,
                "country": None,
                "grid": None,
                "county": None,
                "fname": None,
                "name": None,
                "source": "qrz",
                "lookup_mode": "exact",
                "error": error,
                "timestamp": int(time.time()),
            }

        if error and not callsign_data:
            raise QRZError(f"QRZ lookup failed for {query_call}: {error}")

        # Extract a small normalized payload
        result = {
            "found": bool(callsign_data),
            "query_call": query_call,
            "returned_call": callsign_data.get("call"),
            "state": callsign_data.get("state"),
            "country": callsign_data.get("country"),
            "grid": callsign_data.get("grid"),
            "county": callsign_data.get("county"),
            "fname": callsign_data.get("fname"),
            "name": callsign_data.get("name"),
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

        # Cache exact query result by original call
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