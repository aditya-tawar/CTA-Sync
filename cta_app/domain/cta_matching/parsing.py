"""
cta_matching.parsing
====================
Turn a campaign file (.html or .eml) into a clean list of CTA candidates.

Why this module exists
----------------------
Raw HTML campaign files have clean <a href> URLs that can be matched directly
against the Claravine "Link" column.  Real *delivered* emails (.eml) do not:

  1. The HTML lives inside a MIME message and is quoted-printable encoded.
  2. Every link is wrapped by one or more tracking / security layers:
       Proofpoint   -> https://urldefense.com/v3/__<url>__;<map>!!...
       MS SafeLinks -> https://*.safelinks.protection.outlook.com/?url=<url>&...
       Salesforce   -> https://links.hcpmessage.mkt6423.com/els/v2/<encrypted>
     The final destination (e.g. benlystahcp.com?cc=em_...) is encrypted inside
     the Salesforce redirect and only resolves when a human clicks it, so it
     CANNOT be recovered from the static email.

  Consequence: for .eml files we match CTAs to the Claravine sheet by
  CTA *name / type* (banner image, learn more, gsk logo, privacy notice,
  contact us ...), not by URL.

This module is pure parsing + classification — no Streamlit / network deps —
so it can be unit-tested headlessly.
"""

from __future__ import annotations

import email
import re
from concurrent.futures.thread import ThreadPoolExecutor
from difflib import SequenceMatcher
from email import policy
from urllib.parse import urlparse, parse_qs, unquote

from bs4 import BeautifulSoup

# File types the campaign-file uploader should accept (drives File_uploader.py).
ACCEPTED_CAMPAIGN_TYPES = ["html", "htm", "eml"]


# ──────────────────────────────────────────────────────────────────────────────
#  URL un-wrapping (tracking / security redirects)
# ──────────────────────────────────────────────────────────────────────────────

# Domains that mean "this href is a redirect/tracker, not the real destination".
TRACKING_DOMAINS = (
    "urldefense.com",
    "urldefense.proofpoint.com",
    "safelinks.protection.outlook.com",
    "mkt6423.com",
    "hcpmessage.mkt6423.com",
    "links.hcpmessage.mkt6423.com",
    "aim-tag.hcn.health",
    "click.email",
    "el2.email",
    "sendgrid.net",
    "go.email",
)

# Per-process cache so Streamlit reruns don't re-hit the network for the
_REDIRECT_CACHE: dict[str, str] = {}

_DEST_PARAM_NAMES = ("click", "url", "u", "redirect", "goto", "target", "destination", "to", "link")

def _embedded_destination(url: str) -> str | None:
    """If a tracker URL carries the real destination in a query param, return it.
    Otherwise None."""
    try:
        p = urlparse(url)
        qs = parse_qs(p.query, keep_blank_values=True)
    except Exception:
        return None
    for key, vals in qs.items():
        if key.lower() in _DEST_PARAM_NAMES and vals:
            candidate = unquote(vals[0]).strip()
            if candidate.startswith(("http://", "https://")):
                return candidate
    return None


def _peel_embedded_destination(url: str, max_passes: int = 5) -> str:
    """Follow destination query params that are visible without network calls."""
    current = str(url or "").strip()
    for _ in range(max_passes):
        embedded = _embedded_destination(current)
        if not embedded or embedded == current:
            break
        current = embedded
    return current


def unwrap_tracking_url(url: str, max_passes: int = 5) -> str:
    """
    Resolve every URL by hitting it with requests + allow_redirects=True.
    and returning the final URL after the redirect chain.
    Falls back to the original URL on any network error.
    """
    if not url:
        return url
    current = url.strip()
    if current in _REDIRECT_CACHE:
        return _REDIRECT_CACHE[current]
    peeled = _peel_embedded_destination(current, max_passes=max_passes)
    try:
        import requests
        resp = requests.get(
            peeled,
            allow_redirects=True,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (CTA-Sync)"},
            stream=True,
            verify=False,
        )
        final = resp.url or current

        embedded = _embedded_destination(final)
        if embedded and embedded != final:
            final = _peel_embedded_destination(embedded, max_passes=max_passes)

        # print(f"[unwrap start={current}")
        # print(f"        status={resp.status_code} final={final}")
        # print(f"        hops={[h.status_code for h in resp.history]}"
        #       f"-> {[h.headers.get('Location') for h in resp.history]}")
        resp.close()
        _REDIRECT_CACHE[current] = final
        return final
    except Exception as e:
        print(f"[unwrap FAIL] {current}  err={e!r}")
        _REDIRECT_CACHE[current] = peeled
        return peeled

def prefetch_urls(urls, max_workers: int = 16) -> None:
    """Resolve many URLs in parallel and warm the cache.

    Call this before iterating links so subsequent unwrap_tracking_url() calls
    became instant cache hits instead of serial network round-trips.
    """
    todo = []
    seen = set()
    for u in urls:
        if not u:
            continue
        s = u.strip()
        if not s or s in _REDIRECT_CACHE or s in seen:
            continue
        seen.add(s)
        todo.append(s)
    if not todo:
        return
    with ThreadPoolExecutor(max_workers=min(max_workers, len(todo))) as pool:
        list(pool.map(unwrap_tracking_url, todo))


def _has_cc_code(url: str) -> bool:
    """True if the URL carries a ?cc= tracking param (case-insensitive).

    CTAs with a cc code must NOT be collapsed by the dedup step, otherwise a
    duplicate / reused cc code loses one of its occurrences before the validator
    can flag every one of them.
    """
    if not url:
        return False
    try:
        qs = parse_qs(urlparse(url).query, keep_blank_values=True)
    except Exception:
        return False
    return any(k.lower() == "cc" for k in qs)


def is_tracking_url(url: str) -> bool:
    """True if the (possibly unwrapped) URL still points at a tracker/redirect,
    meaning its final destination is not directly comparable to a Claravine URL.
    """
    if not url:
        return False
    low = url.lower()
    return any(d in low for d in TRACKING_DOMAINS)


# ──────────────────────────────────────────────────────────────────────────────
#  .eml  ->  HTML
# ──────────────────────────────────────────────────────────────────────────────

def extract_html_from_file(filename: str, data: bytes) -> str:
    """Return the HTML body for a campaign file.

    * .eml  -> parse MIME, return the text/html part (decoded from
               quoted-printable / base64 automatically by the email package).
    * .html/.htm/anything else -> decode bytes as text.
    """
    name = (filename or "").lower()

    if name.endswith(".eml"):
        msg = email.message_from_bytes(data, policy=policy.default)

        html_parts, text_parts = [], []
        for part in msg.walk():
            ctype = part.get_content_type()
            if part.get_filename():  # skip real attachments
                continue
            if ctype == "text/html":
                try:
                    html_parts.append(part.get_content())
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    html_parts.append(payload.decode("utf-8", "replace"))
            elif ctype == "text/plain":
                try:
                    text_parts.append(part.get_content())
                except Exception:
                    pass

        if html_parts:
            return "\n".join(html_parts)
        if text_parts:  # email had no HTML alternative
            return "<pre>" + "\n".join(text_parts) + "</pre>"
        return ""

    # Plain HTML file
    return data.decode("utf-8", errors="replace")


# ──────────────────────────────────────────────────────────────────────────────
#  CTA name normalisation + image classification
# ──────────────────────────────────────────────────────────────────────────────

# Synonyms so email alt-text lines up with Claravine "Creative Tactic Call to
# Action" naming.  e.g. an image alt of "GSK Brandmark" should match "gsk logo".
_NAME_ALIASES = {
    "brandmark": "logo",
    "brand mark": "logo",
}

_SOCIAL_WORDS = ("linkedin", "facebook", "instagram", "twitter", " x icon", "x icon", "youtube")
_LOGO_WORDS = ("logo", "brandmark", "brand mark")


def normalize_cta_name(s: str) -> str:
    """Lower-case, collapse whitespace, and apply CTA-name synonyms."""
    s = re.sub(r"\s+", " ", str(s or "").strip().lower())
    for src, dst in _NAME_ALIASES.items():
        if src in s:
            s = s.replace(src, dst)
    return s


def looks_like_social(alt: str) -> bool:
    a = " " + normalize_cta_name(alt) + " "
    return any(w in a for w in _SOCIAL_WORDS)


def looks_like_logo(alt: str) -> bool:
    return any(w in normalize_cta_name(alt) for w in _LOGO_WORDS)


# ──────────────────────────────────────────────────────────────────────────────
#  CTA extraction
# ──────────────────────────────────────────────────────────────────────────────

# Matches an inline "display:none" (tolerant of spacing) — and the Outlook
# "mso-hide:all" equivalent — used by responsive emails to hide the desktop or
# mobile copy of a CTA. Anything inside such a container is a hidden twin and
# must be skipped so it doesn't show up as a duplicate.
_HIDDEN_STYLE_RE = re.compile(r"display\s*:\s*none|mso-hide\s*:\s*all", re.I)


def _is_hidden(tag) -> bool:
    """True if the tag, or any ancestor, is hidden via inline style/attribute.

    Walks up the DOM because hiding is usually applied to a wrapping <div>/<td>
    (the whole desktop- or mobile-only block), not the <a> itself.
    """
    for node in (tag, *tag.parents):
        get = getattr(node, "get", None)
        if get is None:
            continue
        style = get("style") or ""
        if style and _HIDDEN_STYLE_RE.search(style):
            return True
        if get("hidden") is not None:  # HTML5 boolean 'hidden' attribute
            return True
    return False


def extract_ctas(html_content: str) -> list[dict]:
    """Extract candidate CTAs from an HTML body.

    Each CTA dict:
        text        visible link text (or image alt as fallback)
        href        tracking-unwrapped URL used for display / matching
        raw_href    the original href exactly as it appeared
        is_image    True if the <a> wraps an <img> and has no text
        alt         the image alt text (if any)
        img_src     the image src URL (if any), used for OCR of banners
        is_tracking True if href is a tracking/redirect link
    """
    soup = BeautifulSoup(html_content, "html.parser")
    ctas: list[dict] = []
    seen: set = set()

    # Drop anchors inside a display:none / mso-hide container (the hidden
    # desktop- or mobile-only copy in a responsive email) so they don't get
    # parsed as duplicate CTAs.
    anchors = [t for t in soup.find_all("a", href=True) if not _is_hidden(t)]

    prefetch_urls(
        (tag.get("href") or "").strip()
        for tag in anchors
        if (tag.get("href") or "").strip()
        and not (tag.get("href") or "").strip().startswith(("#", "mailto:", "tel:"))
    )

    for tag in anchors:
        raw_href = (tag.get("href") or "").strip()

        # Skip empty, in-page anchors, mailto / tel links.
        if (not raw_href or raw_href.startswith("#")
                or raw_href.startswith("mailto:") or raw_href.startswith("tel:")):
            continue

        href = unwrap_tracking_url(raw_href)

        raw_text = tag.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", raw_text).strip()

        img = tag.find("img")
        alt = ""
        img_src = ""
        if img is not None:
            alt = re.sub(r"\s+", " ", (img.get("alt") or "").strip())
            img_src = (img.get("src") or "").strip()

        is_image = bool(img is not None and not text)
        if is_image:
            text = alt  # provisional; banner labelling may overwrite this

        if not text and not alt:
            try:
                host = urlparse(href).netloc or urlparse(raw_href).netloc or ""
            except Exception:
                host = ""
            text = f"(unnamed link -> (host)" if host else "(unnamed link)"

        # Keep every cc-bearing CTA so duplicate / reused cc codes all reach the
        # validator and can each be flagged as failed in the report. Only links
        # WITHOUT a cc code are collapsed (e.g. a logo repeated in header/footer).
        key = (text.lower(), href.lower(), is_image)
        if key in seen and not (_has_cc_code(raw_href) or _has_cc_code(href)):
            continue
        seen.add(key)

        ctas.append({
            "text": text,
            "href": href,
            "raw_href": raw_href,
            "is_image": is_image,
            "alt": alt,
            "img_src": img_src,
            "is_tracking": is_tracking_url(raw_href) or is_tracking_url(href),
        })

    return ctas


# ──────────────────────────────────────────────────────────────────────────────
#  Banner OCR
# ──────────────────────────────────────────────────────────────────────────────

# Image src -> OCR text. Per-process, so Streamlit reruns don't re-download/OCR.
_OCR_CACHE: dict[str, str] = {}
_OCR_ENGINE = None

# Minimum similarity between a Claravine name and an OCR phrase. Allows small
# OCR slips ("Hepatitls") without matching unrelated words.
_OCR_MIN_RATIO = 0.85


def ocr_image_text(src: str) -> str:
    """Download an http(s) image and return the text OCR reads from it.

    Uses rapidocr-onnxruntime (pip only, no system binary). Returns "" when the
    package is missing, the image can't be fetched, or no text is found, so the
    caller simply falls back to alt-text naming.
    """
    global _OCR_ENGINE
    if not src or not src.lower().startswith(("http://", "https://")):
        return ""
    if src in _OCR_CACHE:
        return _OCR_CACHE[src]
    text = ""
    try:
        import requests
        from rapidocr_onnxruntime import RapidOCR

        if _OCR_ENGINE is None:
            _OCR_ENGINE = RapidOCR()
        resp = requests.get(src, timeout=10, headers={"User-Agent": "Mozilla/5.0 (CTA-Sync)"})
        resp.raise_for_status()
        result, _ = _OCR_ENGINE(resp.content)
        # result rows are [box, text, score], top -> bottom.
        text = " ".join(row[1] for row in (result or []))
    except Exception as e:
        print(f"[ocr FAIL] {src}  err={e!r}")
    _OCR_CACHE[src] = text
    return text


def _words(s: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", normalize_cta_name(s)).split()


def _phrase_in_text(name: str, text_words: list[str]) -> bool:
    """True if the words of `name` appear in order in `text_words` (fuzzy)."""
    name_words = _words(name)
    n = len(name_words)
    if not n:
        return False
    target = " ".join(name_words)
    return any(
        SequenceMatcher(None, target, " ".join(text_words[i:i + n])).ratio() >= _OCR_MIN_RATIO
        for i in range(len(text_words) - n + 1)
    )


def _best_ocr_name(ocr_text: str, available: dict[str, int]) -> str | None:
    """Pick the longest Claravine name found in the OCR text that still has a
    free row. Longest wins so "chronic hepatitis b" beats a bare "hepatitis"."""
    text_words = _words(ocr_text)
    found = [name for name, free in available.items() if free > 0 and _phrase_in_text(name, text_words)]
    return max(found, key=len) if found else None


def _name_matches_any(name_norm: str, csv_names_norm: list[str]) -> bool:
    if not name_norm:
        return False
    for cn in csv_names_norm:
        if not cn:
            continue
        if name_norm == cn or name_norm in cn or cn in name_norm:
            return True
    return False


def label_image_ctas(ctas: list[dict], csv_names: list[str]) -> list[dict]:
    """Classify image CTAs using their alt text as the cta name.

    An image link is a *banner* when its alt text does not already correspond
    to a named CSV CTA (e.g. "learn more") and is not a social icon or a logo.
    Banners whose alt text doesn't name a CSV CTA are OCR'd, and the Claravine
    name found in the image text becomes the CTA name (see _name_banners_by_ocr).
    """
    csv_names_norm = [normalize_cta_name(n) for n in csv_names if str(n).strip()]
    unnamed_banners: list[dict] = []

    for c in ctas:
        if not c.get("is_image"):
            c.setdefault("cta_type", "text")
            continue

        alt = c.get("alt", "")
        alt_norm = normalize_cta_name(alt)

        if looks_like_social(alt):
            c["cta_type"] = "social"
            c["text"] = alt or "Social Icon"
            continue

        if looks_like_logo(alt):
            c["cta_type"] = "logo"
            # "GSK Brandmark" -> "gsk logo" so it matches the Claravine name.
            c["text"] = alt_norm if "logo" in alt_norm else (alt_norm + " logo").strip()
            continue

        if _name_matches_any(alt_norm, csv_names_norm):
            # alt already names a real CTA (e.g. "LEARN MORE") -> keep it.
            c["cta_type"] = "named-image"
            c["text"] = alt
            continue

        # Otherwise it is a content banner -> try to name it from its pixels.
        c["cta_type"] = "image"
        if alt:
            c["text"] = alt
        unnamed_banners.append(c)

    _name_banners_by_ocr(ctas, unnamed_banners, csv_names)
    return ctas


def _name_banners_by_ocr(ctas: list[dict], banners: list[dict], csv_names: list[str]) -> None:
    """Rename banners to the Claravine CTA name OCR finds in the image.

    Only names with a free sheet row are used: a row already taken by another
    CTA with that exact name (e.g. a real "learn more" button) can't be claimed
    by a banner that also says "learn more". Sets `ocr_text` on renamed banners
    so the report can say where the name came from.
    """
    if not banners or not csv_names:
        return
    available: dict[str, int] = {}
    original: dict[str, str] = {}  # normalized -> name as written in the sheet
    for raw in csv_names:
        name = normalize_cta_name(raw)
        if not name:
            continue
        available[name] = available.get(name, 0) + 1
        original.setdefault(name, str(raw).strip())
    banner_ids = {id(b) for b in banners}
    for c in ctas:
        name = normalize_cta_name(c.get("text", ""))
        if id(c) not in banner_ids and available.get(name, 0) > 0:
            available[name] -= 1

    for c in banners:
        ocr_text = ocr_image_text(c.get("img_src", ""))
        name = _best_ocr_name(ocr_text, available) if ocr_text else None
        if name:
            available[name] -= 1
            c["text"] = original[name]
            c["ocr_text"] = ocr_text


def extract_campaign_ctas(filename: str, file_bytes: bytes, csv_names: list[str]) -> list[dict]:
    """High-level entry point: campaign file bytes -> classified CTA list.

    Handles .html and .eml, unwraps tracking links, and names banner images
    from their alt text or, failing that, OCR against the Claravine CTA names.
    """
    html_content = extract_html_from_file(filename, file_bytes)
    ctas = extract_ctas(html_content)
    label_image_ctas(ctas, csv_names or [])
    return ctas
