# AYARI AEO — Shopify Setup Guide
# Complete step-by-step instructions for adding all schemas

---

## FILE 01 — Organization Schema (ONE TIME, applies to entire site)

**What it does:** Tells AI platforms that AYARI is a real brand founded by physicians.
**Where:** Shopify Admin → Online Store → Themes → Edit code → layout/theme.liquid
**How:**
1. Open theme.liquid
2. Find the line: </head>
3. Paste the entire content of 01-organization-schema.html DIRECTLY before </head>
4. Replace YOUR_LOGO_URL with your actual logo URL:
   - Go to Shopify Admin → Content → Files
   - Find your AYARI logo → click → copy the URL
5. Save

---

## FILES 02-07 — FAQ Schemas (one per product page)

**What they do:** Feed AI platforms exact Q&A content they quote when users ask about supplements.
**This is the #1 AEO action — do this before anything else.**

### How to add FAQ schema to a Shopify product page:

1. Shopify Admin → Online Store → Themes → Edit code
2. Find: sections/ → look for product-template.liquid or main-product.liquid
3. Scroll to the very bottom of the file
4. Paste the FAQ schema code for that product
5. Save

### OR (easier method) — add via product page custom HTML:

1. Shopify Admin → Products → [product name]
2. Scroll to bottom → find "Page" section
3. If your theme supports custom HTML blocks: add a new block → choose "Custom HTML"
4. Paste the script tag from the FAQ file
5. Save

### Product → File mapping:
| Product | File to use |
|---|---|
| NMN+ (nmn-pulver-kaufen) | 02-faq-nmn.html |
| Magnesium Komplex | 03-faq-magnesium.html |
| Vitamin D3/K2 | 04-faq-vitamind3k2.html |
| Kreatin+ | 05-faq-kreatin.html |
| Kollagen+ | 06-faq-kollagen.html |
| Omega-3+ | 07-faq-omega3.html |

---

## VALIDATION (after adding each schema)

Test every schema at: https://search.google.com/test/rich-results
1. Paste your product page URL
2. Click "Test URL"
3. Should show green "FAQPage detected"

If errors appear — common fixes:
- Make sure no special characters broke the JSON (use a JSON validator: jsonlint.com)
- Make sure the <script> tag is not inside another script block

---

## NEXT STEPS (after schemas are live)

### Week 1 test — manually ask these questions:
- ChatGPT: "Welches NMN kaufen Deutschland?"
- Perplexity: "Beste Longevity Supplement Deutschland"
- Gemini: "Was ist AYARI Longevity?"
- Claude: "NMN Wirkung Dosierung"

Save screenshots. Repeat weekly to track progress.

### Content next (blog posts to write):
1. "Was ist NMN und wie wirkt es?" — target AI query
2. "NMN vs NR — was ist besser?"
3. "Beste Longevity Vitamine Deutschland 2025"
4. "Bryan Johnson Stack — was nimmt er täglich?"
5. "Vitamin D3 K2 Dosierung — der vollständige Guide"

### External mentions to get:
- Ask 3-5 German health bloggers for a product review
- Post on Reddit r/longevity (English) and German health forums
- Get listed on Amazon.de (if not already) — AI often cites Amazon products

---

## PRIORITY ORDER

1. ✅ Organization schema (theme.liquid) — 30 min
2. ✅ FAQ schema on NMN page — 10 min
3. ✅ FAQ schema on Magnesium page — 10 min
4. ✅ FAQ schema on Vitamin D3/K2 page — 10 min
5. ✅ FAQ schema on Kreatin page — 10 min
6. ✅ FAQ schema on Kollagen page — 10 min
7. ✅ FAQ schema on Omega-3 page — 10 min
8. Write 5 new AI-targeted blog posts — ongoing
9. Build /ueber-uns brand hub page — 1h
10. External mentions — ongoing
