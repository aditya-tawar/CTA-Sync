"""URL normalization and CTA URL validation rules."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse

import pandas as pd
import requests


def normalize_text(value: str) -> str:
    """Strip, lowercase, and collapse whitespace for CTA text comparison."""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def normalize_url(url: str) -> str:
    try:
        stripped_url = url.strip()
        parsed_url = urlparse(stripped_url)
        params = parse_qs(parsed_url.query, keep_blank_values=True)
        sorted_query = urlencode(sorted(params.items()), doseq=True)
        normalized_base = (
            f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}".rstrip("/")
        )
        return normalized_base + (f"?{sorted_query}" if sorted_query else "")
    except Exception:
        return url.strip()


def extract_cc_code(url: str) -> str:
    """Return the value of the ?cc= query param (case-insensitive), or '' if absent."""
    try:
        params = parse_qs(urlparse(url.strip()).query, keep_blank_values=True)
    except Exception:
        return ""
    for key, values in params.items():
        if key.lower() == "cc" and values:
            return values[0].strip()
    return ""


def params_of(url: str) -> dict:
    try:
        return parse_qs(urlparse(url).query, keep_blank_values=True)
    except Exception:
        return {}


def base_of(url: str) -> str:
    try:
        parsed_url = urlparse(url)
        return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}".rstrip("/")
    except Exception:
        return url


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


def check_url_accessible(url: str) -> tuple[bool, str]:
    """Fail only when there is definitive evidence that a URL is broken."""
    if not url or not url.strip():
        return False, "Invalid URL - URL is empty or blank."

    try:
        parsed_url = urlparse(url.strip())
        if not parsed_url.scheme or parsed_url.scheme not in ("http", "https"):
            return False, (
                f"Invalid URL - must start with 'http://' or 'https://': '{url[:80]}'"
            )
        if not parsed_url.netloc or "." not in parsed_url.netloc.split(":")[0]:
            return False, f"Invalid URL - missing or invalid domain: '{url[:80]}'"
        if " " in url.strip():
            return False, (
                f"Invalid URL - contains spaces: '{url[:80]}'. Replace spaces with '%20'."
            )
    except Exception:
        return False, f"Invalid URL - could not parse: '{url[:80]}'"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = requests.head(
            url.strip(), timeout=6, allow_redirects=True, headers=headers
        )
        if response.status_code in (405, 406):
            response = requests.get(
                url.strip(),
                timeout=6,
                allow_redirects=True,
                headers=headers,
                stream=True,
            )
            response.close()

        if response.status_code == 404:
            return False, (
                f"Page not accessible - 404 Not Found: '{url[:80]}'. "
                "This page does not exist. Verify the URL is correct."
            )
        if response.status_code == 410:
            return False, (
                f"Page not accessible - 410 Gone: '{url[:80]}'. "
                "This page has been permanently removed."
            )
        return True, ""

    except requests.exceptions.ConnectionError as error:
        error_text = str(error).lower()
        if (
            "name or service not known" in error_text
            or "nodename nor servname" in error_text
            or "getaddrinfo failed" in error_text
            or "name resolution" in error_text
        ):
            return False, (
                f"Invalid URL - domain does not exist: '{url[:80]}'. "
                "Check the domain name is spelled correctly."
            )
        return True, ""

    except Exception:
        return True, ""


def _find_channel_code_column(csv_row: pd.Series) -> str | None:
    for column in csv_row.index:
        normalized = re.sub(r"[^a-z0-9]", "", str(column).lower())
        if normalized in ("channelcode", "channel"):
            return column
    return None


def _channel_code_issue(html_href: str, csv_row: pd.Series) -> dict | None:
    """Verify the URL's cc=<prefix>_... prefix matches the CSV row's Channel Code."""
    cc = extract_cc_code(html_href)
    if not cc:
        return None
    channel_col = _find_channel_code_column(csv_row)
    if not channel_col:
        return None
    expected = str(csv_row.get(channel_col, "") or "").strip().lower()
    if not expected or expected == "nan":
        return None
    actual_prefix = (cc.split("_", 1)[0] if "_" in cc else cc).lower()
    if actual_prefix == expected:
        return None
    return {
        "reason": (
            f"Channel code mismatch: URL cc='{cc}' starts with '{actual_prefix}', "
            f"but Claravine 'Channel Code' for this row is '{expected}'."
        ),
        "fix": (
            f"Update the cc code prefix in the URL to '{expected}_…' so it matches "
            "the Channel Code column in the Claravine CSV."
        ),
    }


def smart_match(html_href: str, csv_row: pd.Series, url_col: str, lp_col: str) -> dict:
    result = _smart_match_url(html_href, csv_row, url_col, lp_col)

    channel_issue = _channel_code_issue(html_href, csv_row)
    if channel_issue:
        result.setdefault("issues", []).append(channel_issue)
        if result.get("status") == "passed":
            result["status"] = "failed"
            result.pop("pass_reason", None)
        elif result.get("status") == "warning":
            result["status"] = "failed"

    return result


def _smart_match_url(html_href: str, csv_row: pd.Series, url_col: str, lp_col: str) -> dict:
    url_ok, url_error = check_url_accessible(html_href)
    if not url_ok:
        return {
            "status": "failed",
            "issues": [
                {
                    "reason": url_error,
                    "fix": (
                        "Correct the URL in the HTML file and ensure the page is live "
                        "and publicly accessible."
                    ),
                }
            ],
        }

    html_url = normalize_url(html_href)
    csv_url_raw = str(csv_row.get(url_col, "") or "").strip()
    csv_lp_raw = str(csv_row.get(lp_col, "") or "").strip()

    if not csv_url_raw:
        return {
            "status": "failed",
            "issues": [
                {
                    "reason": (
                        "Missing - Email CTA URL column is empty in the Claravine "
                        "CSV for this row."
                    ),
                    "fix": (
                        "Add the correct Email CTA URL to the Claravine CSV."
                    ),
                }
            ],
        }

    csv_url = normalize_url(csv_url_raw)
    csv_lp = normalize_url(csv_lp_raw) if csv_lp_raw else ""

    if html_url == csv_url:
        return {
            "status": "passed",
            "issues": [],
            "pass_reason": "URL exactly matches Email CTA URL ✓",
        }

    if csv_lp and html_url == csv_lp:
        return {
            "status": "passed",
            "issues": [],
            "pass_reason": "URL exactly matches Landing Page URL ✓",
        }

    html_base = base_of(html_url)
    csv_base = base_of(csv_url)
    landing_page_base = base_of(csv_lp) if csv_lp else ""

    if html_base == csv_base:
        return {
            "status": "failed",
            "issues": [
                {
                    "reason": (
                        "URL Mismatch - base URL matches but the full URL does not "
                        "exactly match the Claravine CSV."
                    ),
                    "fix": (
                        "Update the HTML URL so it matches the Claravine 'Link' "
                        f"value exactly: {csv_url_raw[:120]}"
                    ),
                }
            ],
        }

    if landing_page_base and html_base == landing_page_base:
        return {
            "status": "warning",
            "issues": [
                {
                    "reason": (
                        "URL matches the Landing Page URL but not the Email CTA URL."
                    ),
                    "fix": (
                        "Review the Claravine CSV and ensure the Email CTA URL is "
                        "populated. Update the HTML href to match it exactly."
                    ),
                }
            ],
        }

    if csv_url and domain_of(html_url) == domain_of(csv_url):
        return {
            "status": "failed",
            "issues": [
                {
                    "reason": (
                        "URL Mismatch - same domain but path differs. "
                        f"HTML: {html_href[:80]} | CSV: {csv_url_raw[:80]}"
                    ),
                    "fix": (
                        "Update the HTML href to exactly match the URL in the "
                        "Claravine CSV."
                    ),
                }
            ],
        }

    return {
        "status": "failed",
        "issues": [
            {
                "reason": (
                    f"URL Mismatch - not found in Claravine CSV: {html_href[:80]}"
                ),
                "fix": (
                    "Check whether this CTA should be tracked. If yes, add the "
                    "exact URL to the Claravine CSV."
                ),
            }
        ],
    }

