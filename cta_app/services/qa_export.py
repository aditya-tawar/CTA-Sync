"""Claravine QA-format Excel exporter (single 'Claravine QA' sheet, inline values)."""

from __future__ import annotations

import email
import re
from email import policy
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

QA_HEADERS = [
    "Email Subject Line",
    "Email Link CTA",
    "Email CT-URL (with query strings)",
    "Email Landing Page URL",
    "Email Tracking Code",
    "Claravine Subject Line",
    "Claravine Link CTA",
    "Claravine CT-URL (with query strings)",
    "Claravine Landing Page URL",
    "Claravine cc= Tracking code",
    "QA Landing Page URL",
    "QA Tracking Code",
    "QA Notes",
]

EMAIL_HEADER_FILL = PatternFill(
    start_color="FFC000", end_color="FFF2CC", fill_type="solid"
)
CLARAVINE_HEADER_FILL = PatternFill(
    start_color="92D050", end_color="C6EFCE", fill_type="solid"
)
QA_HEADER_FILL = PatternFill(
    start_color="00B0F0", end_color="BDD7EE", fill_type="solid"
)
HEADER_FONT= Font(color="000000", bold=True)
PASS_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE",
                        fill_type="solid")
FAIL_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE",
                        fill_type="solid")


def _header_fill_for(col_idx: int) -> PatternFill:
    """Take column index as input and return color based on that
    For Email related columns: `EMAIL_HEADER_FILL`
    for CLARAVINE related columns: `CLARAVINE_HEADER_FILL`
    for QA related columns: `QA_HEADER_FILL`
    """
    if 1 <= col_idx <= 5:
        return EMAIL_HEADER_FILL
    if 6 <= col_idx <= 10:
        return CLARAVINE_HEADER_FILL
    return QA_HEADER_FILL


def _norm_col(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _norm_text(value) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _resolve_column_name(headers: list[str],
                         *keyword_groups: tuple[str, ...]) -> str | None:
    """Return the original header name whose normalized form contains all keywords in any group."""
    for group in keyword_groups:
        norm_keys = [_norm_col(k) for k in group]
        for header in headers:
            normalized = _norm_col(header)
            if all(k in normalized for k in norm_keys):
                return header
    return None


def _extract_eml_subject(file_bytes: bytes) -> str:
    try:
        msg = email.message_from_bytes(file_bytes, policy=policy.default)
        return str(msg.get("Subject", "") or "").strip()
    except Exception:
        return ""


def _file_subject(filename: str, file_bytes: bytes) -> str:
    if filename.lower().endswith(".eml"):
        return _extract_eml_subject(file_bytes)
    return ""


def _strip_query(url: str) -> str:
    if not url:
        return ""
    s = str(url).strip()
    q = s.find("?")
    if q < 0:
        return s
    frag = s.find("#", q)
    return s[:q] + (s[frag:] if frag >= 0 else "")


def _extract_cc(url: str) -> str:
    try:
        params = parse_qs(urlparse(str(url).strip()).query,
                          keep_blank_values=True)
    except Exception:
        return ""
    for key, values in params.items():
        if key.lower() == "cc" and values:
            return values[0].strip()
    return ""

_NULLISH_VALUES = {"", "nan", "none", "null", "np", "n/a", "na", "not provided"}

def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    s = str(value).strip()
    return "" if s.lower() in ("nan", "none") else s

def _claravine_value(value) -> str:
    """Read a claravine cell, returning 'na' when the source value is nullish"""
    raw = _cell_text(value)
    return "na" if raw.lower() in _NULLISH_VALUES else raw


def _build_qa_notes(cta: dict) -> str:
    issues = cta.get("issues") or []
    if not issues:
        return ""
    lines: list[str] = []
    numbered = len(issues) > 1
    for idx, raw in enumerate(issues, 1):
        if isinstance(raw, dict):
            reason = (raw.get("reason") or "").strip()
            fix = (raw.get("fix") or "").strip()
        else:
            reason, fix = str(raw).strip(), ""
        label = f"({idx}) " if numbered else ""
        lines.append(f"{label}{reason}")
        if fix:
            lines.append(f"    Fix: {fix}")
    return "\n".join(lines)

def _norm_url_for_compare(value: str) -> str:
    """Loose comparison: lowercase strip whitespace and trailing slash."""
    s = str(value or "")
    s = re.sub(r"\s+", "", s)
    return s.rstrip("/").lower()

def _extract_test_number(subject: str) -> str:
    """Pull a leading test marker like 'T1' / 'T2' out of an email subject."""
    if not subject:
        return ''
    m = re.search(r"\bT\d+\b", subject)
    return m.group(0) if m else ""

def _first_nonblank(csv_df: pd.DataFrame, col: str | None) -> str:
    """Return the first non-blank value in a column (campaign-level metadata
    typically repeats per row, so the first usable value is good enough)."""
    if not col or col not in csv_df.columns:
        return ""
    for val in csv_df[col]:
        text = _cell_text(val)
        if text and text.lower() not in _NULLISH_VALUES:
            return text
    return ""


def build_qa_workbook(
        campaign_files_data: dict,
        csv_df: pd.DataFrame,
        cta_results: list,
        name_col: str,
        campaign_name: str = "",
) -> tuple[BytesIO, str]:
    """Build a single-sheet Claravine QA workbook with fully-resolved values."""
    wb = Workbook()
    wb.properties.creator = "Indegene"
    wb.properties.title = "CTA Sync - Claravine QA Report"
    wb.properties.description = "Campaign CTA validation report generated by CTA Sync, by Indegene."
    ws = wb.active
    ws.title = "Claravine QA"

    headers = list(csv_df.columns)
    subj_col_name = _resolve_column_name(headers, ("subjectline",),
                                         ("subject",))
    link_col_name = _resolve_column_name(headers, ("link",))
    cta_name_col = _resolve_column_name(headers, ("calltoaction",),
                                        ("ctaname",))
    lp_col_name = _resolve_column_name(
        headers, ("landingpage",), ("landing", "url"), ("destination", "url")
    )
    cc_col_name = _resolve_column_name(
        headers, ("usp", "pattern"), ("topleve", "pattern"),
        ("tracking", "code")
    )

    brand_col_name = _resolve_column_name(headers, ("brandname",), ("brand",))
    wave_col_name = _resolve_column_name(
        headers, ("creativetacticwavenumber", ), ("wavenumber",),("wave",)
    )
    docid_col_name = _resolve_column_name(headers, ("documentid",), ("docid",))


    name_lookup: dict[str, pd.Series] = {}
    if name_col in csv_df.columns:
        for _, row in csv_df.iterrows():
            key = _norm_text(row.get(name_col, ""))
            if key and key not in name_lookup:
                name_lookup[key] = row

    subject_cache: dict[str, str] = {}
    for fname, fbytes in campaign_files_data.items():
        subject_cache[fname] = _file_subject(fname, fbytes)

    brand = _first_nonblank(csv_df, brand_col_name)
    wave = _first_nonblank(csv_df, wave_col_name)
    document_id = _first_nonblank(csv_df, docid_col_name)
    first_subject = next(
        (subject_cache[f] for f in campaign_files_data if subject_cache.get(f)), ""
    )
    test_number = _extract_test_number(first_subject)

    name_parts = [p for p in (brand, wave, test_number, document_id) if p]
    email_name = "_".join(name_parts) if name_parts else (
        next(iter(campaign_files_data.keys()), "") if campaign_files_data else ""
    )
    ws["A1"] = f"Email name: {email_name}".rstrip()
    ws["A1"].font = Font(bold=True)

    if document_id:
        ws["D1"] = document_id
        ws["D1"].font = Font(bold=True)

    for col_idx, header in enumerate(QA_HEADERS, 1):
        cell = ws.cell(2, col_idx, header)
        cell.fill = _header_fill_for(col_idx)
        cell.font = HEADER_FONT
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )

    grouped: dict[str, list] = {}
    for cta in cta_results:
        subject = subject_cache.get(cta.get("source", ""), "") or ""
        grouped.setdefault(subject, []).append(cta)

    row_num = 3
    first_group = True
    for subject, ctas in grouped.items():
        if not first_group:
            row_num += 1  # blank separator row between subject groups
        first_group = False
        for cta in ctas:
            email_url = cta.get("url", "") or ""
            email_lp = _strip_query(email_url)
            email_cc = _extract_cc(email_url)

            matched_row = None
            matched_row_index = cta.get("matched_row_index")
            if matched_row_index is not None:
                try:
                    idx = int(matched_row_index)
                    if idx in csv_df.index:
                        matched_row = csv_df.loc[idx]
                    elif 0 <= idx < len(csv_df):
                        matched_row = csv_df.iloc[idx]
                except (TypeError, ValueError):
                    matched_row = None

            if matched_row is None:
                matched_key = _norm_text(cta.get("matched_name", ""))
                matched_row = name_lookup.get(matched_key)

            if matched_row is not None:
                clr_subj = (
                    _claravine_value(matched_row.get(subj_col_name))
                    if subj_col_name
                    else "na"
                )
                clr_cta_name = (
                    _cell_text(matched_row.get(cta_name_col))
                    if cta_name_col
                    else ""
                )
                clr_url = (
                    _cell_text(matched_row.get(link_col_name))
                    if link_col_name
                    else ""
                )
                clr_lp = (
                    _cell_text(
                        matched_row.get(lp_col_name)) if lp_col_name else ""
                )
                clr_cc = (
                    _cell_text(
                        matched_row.get(cc_col_name)) if cc_col_name else ""
                )
                if not clr_cc and clr_url:
                    clr_cc = _extract_cc(clr_url)
            else:
                clr_subj = clr_cta_name = clr_url = clr_lp = clr_cc = ""

            ws.cell(row_num, 1, subject)
            ws.cell(row_num, 2, cta.get("text", ""))
            ws.cell(row_num, 3, email_url)
            ws.cell(row_num, 4, email_lp)
            ws.cell(row_num, 5, email_cc)
            ws.cell(row_num, 6, clr_subj)
            ws.cell(row_num, 7, clr_cta_name)
            ws.cell(row_num, 8, clr_url)
            ws.cell(row_num, 9, clr_lp)
            ws.cell(row_num, 10, clr_cc)


            lp_pass = (
                bool(email_lp)
                and bool(clr_lp)
                and _norm_url_for_compare(email_lp) == _norm_url_for_compare(clr_lp)
            )
            # A duplicate / reused cc code (flagged on the CTA by the validator,
            # either email-side or Claravine-sheet-side) must fail the Tracking
            # Code cell too — the plain email-vs-row cc comparison can't see it
            # because each duplicate row's own cc still matches the email.
            has_dup_cc = any(
                "duplicate cc code"
                in ((i.get("reason", "") if isinstance(i, dict) else str(i)).lower())
                for i in (cta.get("issues") or [])
            )
            cc_pass = (
                bool(email_cc)
                and bool(clr_cc)
                and (email_cc == clr_cc)
                and not has_dup_cc
            )
            ws.cell(row_num, 11, "pass" if lp_pass else "fail")
            ws.cell(row_num, 12, "pass" if cc_pass else "fail")
            ws.cell(row_num, 11).fill = PASS_FILL if lp_pass else FAIL_FILL
            ws.cell(row_num, 12).fill = PASS_FILL if cc_pass else FAIL_FILL

            extra_notes: list[str] = []
            if not lp_pass:
                if not email_lp:
                    extra_notes.append("Landing Page URL: email URL is empty.")
                elif not clr_lp:
                    extra_notes.append(
                        "Landing Page URL: Claravine 'Landing Page URL' column is "
                        "empty for the matched row."
                    )
                else:
                    extra_notes.append(
                        f"Landing Page URL mismatch - email: {email_lp} | "
                        f"Claravine: {clr_lp}"
                    )
            if not cc_pass:
                if not email_cc:
                    extra_notes.append("Tracking Code: no cc= parameter in email URL.")
                elif not clr_cc:
                    extra_notes.append(
                        "Tracking Code: Claravine cc/tracking-code column is empty"
                        "for the matched row."
                    )
                elif email_cc != clr_cc:
                    extra_notes.append(
                        f"Tracking Code mismatch - email cc='{email_cc}' | "
                        f"Claravine cc='{clr_cc}'"
                    )
                # else: cc values are equal but the cell still failed because the
                # code is duplicated — that reason is already in _build_qa_notes.
            notes = _build_qa_notes(cta)
            if extra_notes:
                notes = (
                    "\n".join([notes, *extra_notes])
                    if notes
                    else "\n".join(extra_notes)
                )
            ws.cell(row_num, 13, notes)
            ws.cell(row_num, 13).alignment = Alignment(
                wrap_text=True, vertical="top"
            )

            row_num += 1

    widths = [38, 28, 56, 40, 22, 28, 28, 56, 40, 22, 14, 14, 56]
    for col_idx, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output, email_name
