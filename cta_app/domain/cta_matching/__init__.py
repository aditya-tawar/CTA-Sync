"""
cta_matching
============
Self-contained feature: extract CTAs from a campaign file (.html or .eml) and
match them against the Claravine sheet.

The host app only needs three things from this package:

    from cta_app.domain.cta_matching import (
        ACCEPTED_CAMPAIGN_TYPES,   # file types the uploader should accept
        extract_campaign_ctas,     # campaign file bytes -> classified CTA list
        match_email_cta,           # match a tracking-link CTA to the sheet by name
    )

Everything else (.eml parsing, URL un-wrapping, banner-image numbering, image
classification) lives here so the original CTA_sync code stays essentially
unchanged.
"""

from .parsing import (
    ACCEPTED_CAMPAIGN_TYPES,
    extract_campaign_ctas,
    extract_html_from_file,
    extract_ctas,
    label_image_ctas,
    normalize_cta_name,
    unwrap_tracking_url,
    is_tracking_url,
)
from .matching import match_email_cta, match_email_ctas_batch

__all__ = [
    "ACCEPTED_CAMPAIGN_TYPES",
    "extract_campaign_ctas",
    "extract_html_from_file",
    "extract_ctas",
    "label_image_ctas",
    "normalize_cta_name",
    "unwrap_tracking_url",
    "is_tracking_url",
    "match_email_cta",
    "match_email_ctas_batch",
]
