"""CTA matching orchestration for campaign files and Claravine data."""

from __future__ import annotations

import pandas as pd

from cta_app.domain.cta_matching import extract_campaign_ctas, match_email_ctas_batch, extract_html_from_file, \
    extract_ctas, label_image_ctas, normalize_cta_name

from .url_validation import extract_cc_code, normalize_text, normalize_url, smart_match
from ..services.allowed_domains import load_allowed_domains, is_domain_allowed


def _is_valid_cta_name(row: pd.Series, name_col: str) -> bool:
    value = row.get(name_col, "")
    if value is None:
        return False
    normalized_value = str(value).strip().lower()
    return bool(normalized_value) and normalized_value != "nan"


def _missing_cta_fail(reason_detail: str) -> dict:
    return {
        "status": "failed",
        "matched_name": "—",
        "matched_by": "none",
        "issues": [
            {
                "reason": f"Missing - {reason_detail}",
                "fix": (
                    "Add this CTA to the Claravine CSV with the correct CTA name "
                    "and Email CTA URL."
                ),
            }
        ],
    }


def _cta_name_matches_csv(cta_text: str, csv_names_norm: list[str]) -> bool:
    cta_norm = normalize_cta_name(cta_text)
    return any(
        cta_norm == csv_name or cta_norm in csv_name or csv_name in cta_norm
        for csv_name in csv_names_norm
        if csv_name
    )


def _is_allowed_or_named_campaign_cta(
    cta: dict,
    allowed_domains: list[str],
    csv_names_norm: list[str],
) -> bool:
    if is_domain_allowed(cta.get("href", ""), allowed_domains):
        return True
    if is_domain_allowed(cta.get("raw_href", ""), allowed_domains):
        return True
    return _cta_name_matches_csv(cta.get("text", ""), csv_names_norm)


def _match_named_row(
    html_cta: dict,
    row: pd.Series,
    name_col: str,
    url_col: str,
    lp_col: str,
    matched_by: str,
) -> dict:
    if not _is_valid_cta_name(row, name_col):
        return _missing_cta_fail(
            f"CTA name is empty or invalid in Claravine CSV for: "
            f"'{html_cta['text'][:80]}'"
        )

    result = smart_match(html_cta["href"].strip(), row, url_col, lp_col)
    result["matched_name"] = row[name_col]
    result["matched_by"] = matched_by
    result["matched_row_index"] = row.name if row.name is not None else None
    return result


def match_cta_to_csv(
    html_cta: dict,
    csv_df: pd.DataFrame,
    name_col: str,
    url_col: str,
    lp_col: str,
) -> dict:
    html_text = normalize_text(html_cta["text"])
    html_href = html_cta["href"].strip()

    candidate_rows = csv_df.copy()
    candidate_rows["_norm_name"] = candidate_rows[name_col].apply(
        lambda value: normalize_text(value)
        if pd.notna(value) and str(value).strip()
        else ""
    )

    name_matches = candidate_rows[candidate_rows["_norm_name"] == html_text]
    if not name_matches.empty:
        return _match_named_row(
            html_cta, name_matches.iloc[0], name_col, url_col, lp_col, "name"
        )

    partial_matches = candidate_rows[
        candidate_rows["_norm_name"].apply(
            lambda csv_name: bool(csv_name)
            and (html_text in csv_name or csv_name in html_text)
        )
    ]
    if not partial_matches.empty:
        return _match_named_row(
            html_cta,
            partial_matches.iloc[0],
            name_col,
            url_col,
            lp_col,
            "name-partial",
        )

    normalized_html_url = normalize_url(html_href)
    for _, row in candidate_rows.iterrows():
        csv_url_raw = str(row.get(url_col, "") or "").strip()
        if not csv_url_raw:
            continue
        if normalized_html_url == normalize_url(csv_url_raw):
            if not _is_valid_cta_name(row, name_col):
                return _missing_cta_fail(
                    "URL matched in Claravine CSV but CTA name is missing/nan "
                    f"for URL: '{html_href[:100]}'"
                )
            result = smart_match(html_href, row, url_col, lp_col)
            result["matched_name"] = row[name_col]
            result["matched_by"] = "url-exact"
            result["matched_row_index"] = row.name if row.name is not None else None
            return result

    html_tokens = set(html_text.split())
    token_matches = candidate_rows[
        candidate_rows["_norm_name"].apply(
            lambda csv_name: bool(csv_name)
            and len(csv_name.split()) >= 2
            and all(token in html_tokens for token in csv_name.split())
        )
    ]
    if not token_matches.empty:
        return _match_named_row(
            html_cta,
            token_matches.iloc[0],
            name_col,
            url_col,
            lp_col,
            "name-token",
        )

    return _missing_cta_fail(
        "CTA not found in Claravine CSV - "
        f"Text: '{html_cta['text'][:80]}' | URL: '{html_href[:100]}'"
    )


def _with_ocr_note(pass_reason: str, cta: dict) -> str:
    """Tell the reviewer when a banner's name was read from the image by OCR."""
    if not pass_reason or not cta.get("ocr_text"):
        return pass_reason
    return f"{pass_reason} Name read from banner image by OCR: '{cta['ocr_text'][:120]}'."


def generate_cta_data(
    campaign_files_data: dict,
    csv_df: pd.DataFrame,
    name_col: str,
    url_col: str,
    lp_col: str,
) -> list:
    results = []
    cta_id = 0

    csv_names = []
    if name_col in csv_df.columns:
        csv_names = [
            str(value).strip()
            for value in csv_df[name_col].dropna().tolist()
            if str(value).strip()
        ]

    allowed_domains = load_allowed_domains()

    for filename, file_bytes in campaign_files_data.items():
        # raw_ctas = extract_campaign_ctas(filename, file_bytes, csv_names)
        html_content = extract_html_from_file(filename, file_bytes)
        raw_ctas = extract_ctas(html_content)
        label_image_ctas(raw_ctas, csv_names or [])

        if allowed_domains:
            csv_names_norm = [normalize_cta_name(name) for name in csv_names]
            filtered_ctas = []
            for cta in raw_ctas:
                if _is_allowed_or_named_campaign_cta(
                    cta, allowed_domains, csv_names_norm
                ):
                    filtered_ctas.append(cta)
                else:
                    print(f"[allowlist drop] text={cta.get('text')!r} "
                          f"raw={cta.get('raw_href')!r} "
                          f"resolved={cta.get('href')!r}")
            raw_ctas = filtered_ctas


        matches = match_email_ctas_batch(
            raw_ctas,
            csv_df,
            name_col,
            url_col,
            lp_col,
            html_matcher=match_cta_to_csv,
        )
        file_start_index = len(results)
        for raw_cta, match in zip(raw_ctas, matches):
            results.append(
                {
                    "id": cta_id,
                    "text": raw_cta["text"],
                    "url": raw_cta["href"],
                    "status": match["status"],
                    "checked": True,
                    "source": filename,
                    "cta_type": raw_cta.get("cta_type", "text"),
                    "issues": match.get("issues", []),
                    "pass_reason": _with_ocr_note(match.get("pass_reason", ""), raw_cta),
                    "matched_name": match.get("matched_name", "—"),
                    "matched_by": match.get("matched_by", "—"),
                    "matched_row_index": match.get("matched_row_index"),
                }
            )
            cta_id += 1
        _flag_duplicate_cc_codes(results[file_start_index:])
        _flag_invalid_cc_format(results[file_start_index:])
        _flag_claravine_duplicate_cc(
            results[file_start_index:], csv_df, name_col, url_col
        )
    return results


def generate_cta_data_multi(
    campaign_files_data: dict,
    claravine_dfs: dict,
    name_col: str,
    url_col: str,
    lp_col: str,
) -> dict:
    """Run validation against each Claravine CSV separately.

    Returns {claravine_filename: [cta_result, ...]} so the UI can render one
    result set per uploaded Claravine file.
    """
    results_by_csv: dict[str, list] = {}
    for csv_name, csv_df in claravine_dfs.items():
        results_by_csv[csv_name] = generate_cta_data(
            campaign_files_data, csv_df, name_col, url_col, lp_col
        )
    return results_by_csv


def _flag_claravine_duplicate_cc(
    file_results: list,
    csv_df: pd.DataFrame,
    name_col: str,
    url_col: str,
) -> None:
    """Flag CTAs whose matched Claravine row shares a cc code with another row.

    For tracking emails (SafeLinks / Proofpoint / Salesforce) the cc code is not
    recoverable from the email href, so duplicate / reused cc codes have to be
    detected on the Claravine 'Link' column itself and then attached to the
    email CTAs that matched those rows.
    """
    if url_col not in csv_df.columns or name_col not in csv_df.columns:
        return

    # cc code -> list of Claravine CTA names using it; and matched row -> cc code.
    cc_to_names: dict[str, list[str]] = {}
    name_norm_to_cc: dict[str, str] = {}
    row_index_to_cc: dict[int, str] = {}
    for _, row in csv_df.iterrows():
        cc = extract_cc_code(str(row.get(url_col, "") or "")).lower()
        if not cc:
            continue
        name = str(row.get(name_col, "") or "").strip()
        cc_to_names.setdefault(cc, []).append(name)
        row_index_to_cc[int(row.name)] = cc
        name_norm = normalize_cta_name(name)
        if name_norm:
            name_norm_to_cc[name_norm] = cc

    duplicates = {cc: names for cc, names in cc_to_names.items() if len(names) >= 2}
    if not duplicates:
        return

    for cta in file_results:
        matched_row_index = cta.get("matched_row_index")
        cc = None
        if matched_row_index is not None:
            try:
                cc = row_index_to_cc.get(int(matched_row_index))
            except (TypeError, ValueError):
                cc = None
        if not cc:
            matched_norm = normalize_cta_name(cta.get("matched_name", "") or "")
            cc = name_norm_to_cc.get(matched_norm)
        if not cc or cc not in duplicates:
            continue
        # Only flag this CTA as a duplicate if the EMAIL link actually carries
        # the duplicated code. If the email uses a different cc than its matched
        # row, that's a cc mismatch (reported separately) — not a deployed
        # duplicate — so don't mislabel it. When the email cc isn't recoverable
        # (e.g. still-wrapped tracking link), fall back to flagging by row.
        email_cc = extract_cc_code(cta.get("url", "") or "").lower()
        if email_cc and email_cc != cc:
            continue
        siblings = ", ".join(f"'{n}'" for n in duplicates[cc])
        cta["status"] = "failed"
        cta.setdefault("issues", []).append(
            {
                "reason": (
                    f"Duplicate cc code '{cc}' in the Claravine sheet — shared by "
                    f"{len(duplicates[cc])} rows: {siblings}."
                ),
                "fix": (
                    "Each Claravine row must use a unique cc code for accurate "
                    "tracking. Assign distinct cc codes to these rows."
                ),
            }
        )


# Every email-channel cc code is expected to carry this prefix (e.g. cc=em_...).
_EXPECTED_CC_PREFIX = "em_"


def _flag_invalid_cc_format(file_results: list) -> None:
    """Fail any CTA whose cc code is present but doesn't start with 'em_'."""
    for cta in file_results:
        cc = extract_cc_code(cta.get("url", ""))
        if not cc:
            continue
        if not cc.lower().startswith(_EXPECTED_CC_PREFIX):
            cta["status"] = "failed"
            cta.setdefault("issues", []).append(
                {
                    "reason": (
                        f"cc code '{cc}' is not in the expected format — it must "
                        f"start with the '{_EXPECTED_CC_PREFIX}' prefix."
                    ),
                    "fix": (
                        f"Update the cc code in the URL so it begins with "
                        f"'{_EXPECTED_CC_PREFIX}' (e.g. cc={_EXPECTED_CC_PREFIX}...)."
                    ),
                }
            )


def _flag_duplicate_cc_codes(file_results: list) -> None:
    """Within a single campaign file, mark any CTAs sharing a 'cc' code as failed."""
    cc_groups: dict[str, list[dict]] = {}
    for cta in file_results:
        cc = extract_cc_code(cta.get("url", ""))
        if cc:
            cc_groups.setdefault(cc.lower(), []).append(cta)

    for cc_value, group in cc_groups.items():
        if len(group) < 2:
            continue
        sibling_texts = [
            f"'{(other['text'] or '')[:40]}'" for other in group
        ]
        for cta in group:
            cta["status"] = "failed"
            cta.setdefault("issues", []).append(
                {
                    "reason": (
                        f"Duplicate cc code '{cc_value}' — shared by "
                        f"{len(group)} CTAs in this file: "
                        f"{', '.join(sibling_texts)}."
                    ),
                    "fix": (
                        "Each CTA must use a unique cc code for accurate tracking. "
                        "Generate distinct cc codes for each CTA in this campaign."
                    ),
                }
            )
