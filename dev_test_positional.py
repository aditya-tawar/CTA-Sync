"""Positional matching test for cta_matching.match_email_ctas_batch.

Synthesises an email with THREE "Learn More" buttons (each with a different
utm_content) plus a Claravine sheet that has three matching rows, and verifies
that the i-th email CTA pairs with the i-th sheet row — surfacing UTM
mismatches that the per-CTA matcher would miss.

Also covers the duplicate-overflow case (4 in email, 3 in sheet).

Run:
    .venv/bin/python dev_test_positional.py
"""
import io
import pandas as pd

from cta_app.domain.cta_matching import match_email_ctas_batch

# ── Synthetic email CTAs (already extracted; DOM/top-bottom order assumed) ──
EMAIL_CTAS = [
    {"text": "Learn More", "href": "https://benlystahcp.com/?utm_content=hero",
     "is_tracking": False, "is_image": False, "alt": ""},
    {"text": "Learn More", "href": "https://benlystahcp.com/?utm_content=middle",
     "is_tracking": False, "is_image": False, "alt": ""},
    {"text": "Learn More", "href": "https://benlystahcp.com/?utm_content=footer",
     "is_tracking": False, "is_image": False, "alt": ""},
    # 4th occurrence -> should overflow.
    {"text": "Learn More", "href": "https://benlystahcp.com/?utm_content=extra",
     "is_tracking": False, "is_image": False, "alt": ""},
]

# ── Synthetic Claravine sheet (sheet order matters) ──────────────────────────
CSV = pd.DataFrame([
    {"Creative Tactic Call to Action": "Learn More",
     "Link": "https://benlystahcp.com/?utm_content=hero",   "Landing page URL": ""},
    {"Creative Tactic Call to Action": "Learn More",
     "Link": "https://benlystahcp.com/?utm_content=middle", "Landing page URL": ""},
    {"Creative Tactic Call to Action": "Learn More",
     "Link": "https://benlystahcp.com/?utm_content=footer", "Landing page URL": ""},
])


# ── Stub html_matcher: exact href compare on a single-row df ─────────────────
# Mirrors the host's match_cta_to_csv just enough to demonstrate that each
# pairing is validated against its OWN row, not row #0.
def stub_html_matcher(cta, csv_df, name_col, url_col, lp_col):
    row = csv_df.iloc[0]
    if cta["href"].strip() == str(row[url_col]).strip():
        return {"status": "passed", "matched_name": row[name_col],
                "matched_by": "url-exact", "issues": [], "pass_reason": "URLs match"}
    return {"status": "failed", "matched_name": row[name_col],
            "matched_by": "url-mismatch",
            "issues": [{"reason": f"URL mismatch — email {cta['href']} vs sheet {row[url_col]}",
                        "fix": "Update one to match the other"}],
            "pass_reason": ""}


print("=" * 90)
print("Positional pairing — 3 'Learn More' in email vs 3 in sheet (matching UTMs)")
print("=" * 90)

results = match_email_ctas_batch(
    EMAIL_CTAS[:3], CSV,
    "Creative Tactic Call to Action", "Link", "Landing page URL",
    html_matcher=stub_html_matcher,
)
for i, (c, r) in enumerate(zip(EMAIL_CTAS[:3], results)):
    print(f"  #{i+1}  email={c['href']:55} -> status={r['status']:6} matched_by={r['matched_by']}")
    assert r["status"] == "passed", f"row #{i+1} should pass — got {r}"
    assert r["matched_by"] == "url-exact-pos", f"row #{i+1} should be position-tagged"
print("PASS — each email CTA paired with its own sheet row\n")


print("=" * 90)
print("Mismatch detection — swap UTMs on email #2, sheet unchanged")
print("=" * 90)
ctas_swapped = [
    EMAIL_CTAS[0],
    {**EMAIL_CTAS[1], "href": "https://benlystahcp.com/?utm_content=WRONG"},
    EMAIL_CTAS[2],
]
results = match_email_ctas_batch(
    ctas_swapped, CSV,
    "Creative Tactic Call to Action", "Link", "Landing page URL",
    html_matcher=stub_html_matcher,
)
for i, (c, r) in enumerate(zip(ctas_swapped, results)):
    print(f"  #{i+1}  email={c['href']:55} -> status={r['status']:6} matched_by={r['matched_by']}")
assert results[0]["status"] == "passed"
assert results[1]["status"] == "failed", "#2 must FAIL — old code would have passed it against row #0"
assert results[2]["status"] == "passed"
print("PASS — per-position UTM divergence surfaced (per-CTA matcher would have missed this)\n")


print("=" * 90)
print("Overflow — 4 'Learn More' in email, only 3 in sheet")
print("=" * 90)
results = match_email_ctas_batch(
    EMAIL_CTAS, CSV,
    "Creative Tactic Call to Action", "Link", "Landing page URL",
    html_matcher=stub_html_matcher,
)
for i, (c, r) in enumerate(zip(EMAIL_CTAS, results)):
    print(f"  #{i+1}  url={c['href']:55} -> status={r['status']:6}")
assert results[3]["status"] == "failed", "4th occurrence must fail (overflow)"
overflow_reasons = [iss["reason"] for iss in results[3]["issues"]]
assert any("Duplicate-label overflow" in r for r in overflow_reasons), \
    f"expected overflow issue, got: {overflow_reasons}"
print("PASS — overflow CTA flagged with 'Duplicate-label overflow'\n")


print("=" * 90)
print("Tracking-link branch — duplicates pair by name without html_matcher")
print("=" * 90)
tracking_ctas = [
    {"text": "Learn More",
     "href": "https://links.hcpmessage.mkt6423.com/els/v2/aaa",
     "is_tracking": True, "is_image": False, "alt": ""},
    {"text": "Learn More",
     "href": "https://links.hcpmessage.mkt6423.com/els/v2/bbb",
     "is_tracking": True, "is_image": False, "alt": ""},
]
results = match_email_ctas_batch(
    tracking_ctas, CSV,
    "Creative Tactic Call to Action", "Link", "Landing page URL",
    html_matcher=None,  # tracking branch ignores html_matcher anyway
)
for i, r in enumerate(results):
    print(f"  #{i+1}  status={r['status']:6} matched_by={r['matched_by']}")
    assert r["status"] == "passed"
    assert r["matched_by"] == "name-pos", \
        f"expected position-tagged name match, got {r['matched_by']}"
print("PASS — tracking-link duplicates each pair with their own sheet row\n")


print("ALL POSITIONAL CHECKS PASSED ✓")
