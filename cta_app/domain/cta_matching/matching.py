"""
cta_matching.matching
=====================
Name/type based matching of email CTAs against the Claravine sheet.

Used only for *tracking* links (delivered .eml), where the destination URL is
encrypted inside a redirect and therefore cannot be compared to the Claravine
"Link" column.  A confirmed CTA-name match is treated as a pass with a note.

Plain HTML links (clean hrefs) are NOT handled here — the main app keeps using
its existing `match_cta_to_csv` URL/UTM validator for those, so this feature
adds behaviour without altering the original matching code.

The result dict shape matches what the app already expects:
    {status, matched_name, matched_by, issues, pass_reason}
"""

from __future__ import annotations

from urllib.parse import urlparse, parse_qs

import pandas as pd

from .parsing import normalize_cta_name


def _url_identity(url) -> tuple[str, str, str]:
    """Return the stable identity of a CTA destination: (host, path, cc).

    Personalization params (uid/cid/mtrc/mcm) and placeholder tokens
    ({{GIGYAID}}, $INS3$, ...) differ by design between a delivered email and
    the Claravine sheet, so they are ignored — only host, path and the cc=
    tracking code define whether two URLs point at the same thing.
    """
    try:
        p = urlparse(str(url or "").strip())
    except Exception:
        return ("", "", "")
    host = (p.netloc or "").lower()
    path = (p.path or "").rstrip("/").lower()
    cc = ""
    try:
        for key, vals in parse_qs(p.query, keep_blank_values=True).items():
            if key.lower() == "cc" and vals:
                cc = vals[0].strip().lower()
                break
    except Exception:
        pass
    return (host, path, cc)


def _url_mismatch_issue(email_href: str, claravine_link) -> dict | None:
    """Compare an email CTA's resolved URL to the Claravine 'Link' by identity.

    Returns a 'URL Mismatch' issue dict when host / path / cc differ, or None
    when they match (or when there's nothing comparable, e.g. an unresolved
    tracking link with no cc — those fall back to name-only matching).
    """
    e_host, e_path, e_cc = _url_identity(email_href)
    if not e_cc:  # email link didn't resolve to a real destination -> skip
        return None
    if claravine_link is None or (isinstance(claravine_link, float) and pd.isna(claravine_link)):
        return None
    c_host, c_path, c_cc = _url_identity(str(claravine_link))
    if not c_cc and not c_host:  # Claravine Link empty -> nothing to compare
        return None

    diffs: list[str] = []
    if c_cc and e_cc != c_cc:
        diffs.append(f"cc code (email '{e_cc}' vs Claravine '{c_cc}')")
    if c_host and e_host != c_host:
        diffs.append(f"domain (email '{e_host}' vs Claravine '{c_host}')")
    if c_path and e_path != c_path:
        diffs.append(f"path (email '{e_path or '/'}' vs Claravine '{c_path or '/'}')")
    if not diffs:
        return None
    return {
        "reason": "URL Mismatch — " + "; ".join(diffs) + ".",
        "fix": (
            "Update the email CTA URL (or the Claravine 'Link') so the domain, "
            "path and cc code match exactly."
        ),
    }


def _is_valid_name(val) -> bool:
    """False if the Claravine CTA name is missing, blank, or literally 'nan'."""
    if val is None:
        return False
    s = str(val).strip().lower()
    return bool(s) and s != "nan"


def _missing_fail(detail: str) -> dict:
    """Standard FAIL response when a CTA can't be matched to the sheet."""
    return {
        "status": "failed",
        "matched_name": "—",
        "matched_by": "none",
        "issues": [{
            "reason": f"Missing — {detail}",
            "fix": (
                "Add this CTA to the Claravine sheet with the correct CTA name, "
                "Email CTA URL, and all required UTM parameters "
                "(utm_source, utm_medium, utm_campaign, utm_id)."
            ),
        }],
        "pass_reason": "",
    }


def match_email_cta(cta: dict, csv_df: pd.DataFrame, name_col: str,
                    url_col: str = None, lp_col: str = None) -> dict:
    """Match a single (tracking) email CTA to the Claravine sheet by name.

    Steps: exact name -> partial name -> token name.  url_col / lp_col are
    accepted for signature parity with the app's HTML matcher but unused, since
    tracking URLs are not directly comparable.
    """
    text_norm = normalize_cta_name(cta.get("text", ""))

    df = csv_df.copy()
    df["_norm_name"] = df[name_col].apply(
        lambda x: normalize_cta_name(x) if pd.notna(x) and str(x).strip() else ""
    )

    def passed(row, matched_by: str) -> dict:
        if not _is_valid_name(row.get(name_col)):
            return _missing_fail(
                f"Matched a row but its CTA name is empty/invalid in the "
                f"Claravine sheet for: '{cta.get('text', '')[:80]}'"
            )
        result = {
            "status": "passed",
            "matched_name": row[name_col],
            "matched_by": matched_by,
            "matched_row_index": row.name if row.name is not None else None,
            "issues": [],
            "pass_reason": (
                f"Matched to Claravine by CTA name '{row[name_col]}'. "
                f"Link is a tracked/redirect URL — final destination is not "
                f"directly verifiable from the email."
            ),
        }

        # If the email link resolved to a real destination, verify its identity
        # (host + path + cc) against the matched Claravine 'Link'. A difference
        # is a URL Mismatch and fails the CTA.
        mismatch = _url_mismatch_issue(
            cta.get("href", ""), row.get(url_col) if url_col else None
        )
        if mismatch:
            result["status"] = "failed"
            result["pass_reason"] = ""
            result["issues"].append(mismatch)
        return result

    # ── Exact name ────────────────────────────────────────────────────────────
    m = df[df["_norm_name"] == text_norm]
    if not m.empty:
        return passed(m.iloc[0], "name")

    # ── Partial name (one contains the other) ─────────────────────────────────
    m = df[df["_norm_name"].apply(
        lambda cn: bool(cn) and (text_norm in cn or cn in text_norm)
    )]
    if not m.empty:
        return passed(m.iloc[0], "name-partial")

    # ── Token name (every word of a multi-word sheet name appears in the CTA) ──
    html_tokens = set(text_norm.split())
    m = df[df["_norm_name"].apply(
        lambda cn: (
            bool(cn) and len(cn.split()) >= 2
            and all(tok in html_tokens for tok in cn.split())
        )
    )]
    if not m.empty:
        return passed(m.iloc[0], "name-token")

    # ── Not found anywhere ────────────────────────────────────────────────────
    return _missing_fail(
        f"CTA not found in the Claravine sheet — "
        f"Text: '{cta.get('text', '')[:80]}' | URL: '{cta.get('href', '')[:100]}'"
    )


def match_email_ctas_batch(
    ctas: list,
    csv_df: pd.DataFrame,
    name_col: str,
    url_col: str = None,
    lp_col: str = None,
    html_matcher=None,
) -> list:
    """Position-aware batch matching for a whole campaign.

    For each normalised CTA name, the i-th email CTA (in DOM order, which equals
    top->bottom / left->right in well-formed email HTML) is paired with the
    i-th Claravine row of that name (in sheet order).  That row is the *only*
    candidate for that CTA — so duplicate-label entries (e.g. three "Learn More"
    buttons) get validated against three *different* Claravine rows instead of
    all collapsing onto row #1.

    Dispatch per CTA:
      * tracking link (or no html_matcher provided)  -> match_email_cta on a
        single-row DataFrame containing just the paired row (name-pass).
      * clean HTML link with html_matcher provided   -> html_matcher (the host
        app's URL/UTM validator) on that single-row DataFrame, so smart_match
        runs against the correct row's URL + UTMs.

    When the email has more occurrences of a name than the sheet does, the
    extras fall back to per-CTA matching against the full sheet (so partial /
    token / URL fall-backs still work) and are decorated with a
    "Duplicate-label overflow" issue so the report flags them.

    Args:
        ctas:         list of CTA dicts from extract_campaign_ctas (DOM order).
        csv_df:       Claravine sheet, with `name_col` populated.
        name_col:     column name holding the Claravine CTA name.
        url_col:      column with the Email CTA URL (passed through).
        lp_col:       column with the Landing Page URL (passed through).
        html_matcher: optional callable(cta, csv_df, name_col, url_col, lp_col)
                      used for non-tracking CTAs — typically the host app's
                      match_cta_to_csv, so URL/UTM validation is preserved.

    Returns: a list of result dicts, one per input CTA, in the same order.
    """
    # ── Group Claravine row indices by normalised name (preserves sheet order) ──
    csv_groups: dict = {}
    for i, val in enumerate(csv_df[name_col].tolist()):
        if pd.notna(val) and str(val).strip():
            key = normalize_cta_name(val)
            csv_groups.setdefault(key, []).append(i)

    consumed: dict = {k: 0 for k in csv_groups}

    def _dispatch(cta: dict, df: pd.DataFrame) -> dict:
        """Pick the right per-CTA matcher (tracking -> name; else URL/UTM)."""
        if cta.get("is_tracking") or html_matcher is None:
            return match_email_cta(cta, df, name_col, url_col, lp_col)
        return html_matcher(cta, df, name_col, url_col, lp_col)

    results: list = []
    for cta in ctas:
        name_norm = normalize_cta_name(cta.get("text", ""))
        group = csv_groups.get(name_norm)

        if group and consumed[name_norm] < len(group):
            # Positional pairing available -> validate against THIS row only.
            row_idx = group[consumed[name_norm]]
            consumed[name_norm] += 1
            single_df = csv_df.iloc[[row_idx]]

            res = _dispatch(cta, single_df)
            res = dict(res)
            res.setdefault("matched_row_index", row_idx)
            # Tag the matched_by so the UI can see this was a positional pair.
            if isinstance(res.get("matched_by"), str) and res["matched_by"] in (
                "name", "name-partial", "name-token", "url-exact",
            ):
                res["matched_by"] = f"{res['matched_by']}-pos"
            results.append(res)
            continue

        # No pair available -> fall back to the full sheet so partial / token /
        # URL fall-backs still work for typos or unique labels.
        res = _dispatch(cta, csv_df)

        if group is not None and res.get("status") != "passed":
            # The name DID exist in the sheet, we just ran out of rows for it.
            # Decorate the fail so the report explains why.
            res = dict(res)
            issues = list(res.get("issues", []))
            issues.insert(0, {
                "reason": (
                    f"Duplicate-label overflow — '{cta.get('text', '')[:40]}' "
                    f"appears more times in the email than in the Claravine "
                    f"sheet ({len(group)} row(s) available, this is "
                    f"occurrence #{consumed[name_norm] + 1})."
                ),
                "fix": (
                    "Add the missing row(s) to the Claravine sheet, or remove "
                    "the extra CTA from the email."
                ),
            })
            res["issues"] = issues
        results.append(res)

    return results
