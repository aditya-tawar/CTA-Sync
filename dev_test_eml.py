"""End-to-end test of the cta_matching pipeline against the GSK sample files.

Exercises the SAME entry points the app uses:
    cta_matching.extract_campaign_ctas(...)  +  cta_matching.match_email_cta(...)
plus the app's column auto-detect.  Run:
    .venv/bin/python dev_test_eml.py
"""
import io
import pandas as pd

from cta_app.domain.cta_matching import extract_campaign_ctas, match_email_cta

EML = "GSK - Sample Docs/T3-VD-47951-9668 Sub2_ Don’t wait — rethink lupus care now.eml"
CSV = "GSK - Sample Docs/pre-processing_MTRC_GSK_US_Prod_Email_Template2026-04-29_14_55_05.csv"


# ── Replicate the app's guess_col / column auto-detect (CTA_sync_main Step 3) ──
def guess_col(cols, *keyword_groups):
    for keywords in keyword_groups:
        for c in cols:
            if all(k in c.lower().strip() for k in keywords):
                return c
    return cols[0]


with open(CSV, "rb") as f:
    csv_df = pd.read_csv(io.BytesIO(f.read()))
csv_df.columns = csv_df.columns.str.strip()
cols = csv_df.columns.tolist()

name_col = guess_col(cols, ["call", "action"], ["cta", "name"], ["link", "name"], ["name"])
url_col = guess_col(cols, ["final", "url"], ["cta", "url"], ["email", "url"], ["link"], ["url"])
lp_col = guess_col(cols, ["landing", "url"], ["landing"], ["destination", "url"], ["final"])
assert (name_col, url_col, lp_col) == (
    "Creative Tactic Call to Action", "Link", "Landing page URL")
print("Column auto-detect: PASS\n" + "=" * 90)

# ── Run the feature exactly like generate_cta_data does ───────────────────────
csv_names = [str(v).strip() for v in csv_df[name_col].dropna().tolist() if str(v).strip()]
with open(EML, "rb") as f:
    ctas = extract_campaign_ctas(EML.rsplit("/", 1)[-1], f.read(), csv_names)

passed = failed = 0
print(f"{'STATUS':6} {'TYPE':12} {'CTA TEXT':30} -> CSV MATCH (matched_by)")
print("-" * 90)
for c in ctas:
    res = match_email_cta(c, csv_df, name_col, url_col, lp_col)
    ok = res["status"] == "passed"
    passed += ok
    failed += (not ok)
    print(f"{'PASS' if ok else 'fail':6} {c.get('cta_type','?'):12} "
          f"{c['text'][:30]:30} -> {res['matched_name']} ({res['matched_by']})")

print("=" * 90)
print(f"Total CTAs: {len(ctas)} | Passed (matched): {passed} | Failed (not in sheet): {failed}")

print("\nClaravine sheet coverage:")
for n in csv_names:
    hit = any(match_email_cta(c, csv_df, name_col)["matched_name"] == n for c in ctas)
    print(f"  {'OK  ' if hit else 'MISS'}{n}")
assert passed == 6, f"expected 6 matched CTAs, got {passed}"
print("\nALL CHECKS PASSED ✓")
