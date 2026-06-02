# AI Search Visibility Auditor V0.3

This is a tiny local MVP for understanding the product idea.

It is not a full SaaS. It has no accounts, no payment system, no dashboard, and no database. A user enters a website URL, and the app checks six basic signals that can help search engines and AI systems understand the site.

## What V0.3 Adds

V0.3 makes the report more useful for real SaaS founders, indie hackers, and SEO freelancers.

New in V0.3:

- AI crawler checks from `robots.txt`.
- Crawler status for `GPTBot`, `OAI-SearchBot`, `ChatGPT-User`, `ClaudeBot`, `PerplexityBot`, and `Google-Extended`.
- `Allowed`, `Blocked`, and `Unknown` crawler labels.
- `Unknown` status for checks that cannot be verified because of SSL errors, HTTP 403, Cloudflare, bot protection, rate limits, timeouts, or connection problems.
- Neutral scoring for `Unknown`: it does not add points and does not remove points.
- `Unable to Verify` status when more than 70% of checks are unknown.
- Weighted scoring based on real-world testing across SaaS, AI, and developer-tool websites.
- More specific Top Fixes, such as `GPTBot is blocked by robots.txt` or `No sitemap.xml found`.
- A stronger copyable report that includes AI crawler readiness.
- A cleaner single-page UI with a polished hero section, responsive cards, clearer audit summaries, and collapsible detailed checks.

## What V0.2 Added

V0.2 keeps the same six checks from V0.1, but makes the output feel more like a simple report for a SaaS founder, indie hacker, or SEO freelancer.

New in V0.2:

- Overall status classification:
  - `Ready for AI Search` for scores from 80 to 100
  - `Needs Optimization` for scores from 50 to 79
  - `Critical Visibility Issues` for scores from 0 to 49
- Top 3 Fixes based on a fixed priority order.
- A short human-readable English summary generated with simple rules, not an AI API.
- A copyable plain-text report with URL, score, status, top fixes, and summary.
- Clearer result labels for each check: `Passed`, `Needs Work`, or `Error`.

## What It Checks

1. `robots.txt`
   - Why it matters: This file tells crawlers which parts of a site they are allowed or not allowed to access.
   - Product meaning: If important crawlers are blocked by mistake, the site may be harder to discover or understand.

2. `sitemap.xml`
   - Why it matters: This file gives crawlers a list of important pages.
   - Product meaning: A small SaaS site often has pricing, docs, blog, comparison, and feature pages. A sitemap helps crawlers find them.

3. `llms.txt`
   - Why it matters: This is an emerging convention for giving AI systems a clear summary of useful site content.
   - Product meaning: It can help a site explain itself more clearly to AI tools, especially when the site has docs, APIs, or product pages.
   - Scoring note: This is treated as an optional AI-readiness enhancement, not a major defect.

4. Title
   - Why it matters: The title is one of the clearest signals describing a page.
   - Product meaning: If the homepage title is missing or vague, both humans and crawlers may struggle to understand the site quickly.

5. Meta Description
   - Why it matters: The meta description summarizes what the page is about.
   - Product meaning: A clear description helps search snippets, sharing previews, and AI summaries understand the product.

6. Schema Markup
   - Why it matters: Schema is structured data that labels things like products, organizations, FAQs, articles, and software apps.
   - Product meaning: It helps machines understand what the content means, not just what the text says.
   - Scoring note: This MVP checks schema visible in the static homepage HTML and may not detect dynamically rendered structured data.

7. AI Crawler Readiness
   - Why it matters: Some AI companies use named crawlers to fetch public web pages.
   - Product meaning: If a crawler is blocked in `robots.txt`, that AI system may have less direct access to the website's public content.

## How To Run Locally

Install Streamlit:

```bash
pip install streamlit
```

Run the app:

```bash
streamlit run app.py
```

Then open the local URL shown in your terminal.

## Deploy To Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. Make sure the repository contains:
   - `app.py`
   - `requirements.txt`
   - `README.md`
3. Go to Streamlit Community Cloud.
4. Create a new app.
5. Select the GitHub repository.
6. Set the main file path to:

```text
app.py
```

7. Deploy the app.

Streamlit Community Cloud will install the packages listed in `requirements.txt` and run the app.

## How The Score Works

V0.3 uses a weighted score with neutral unknowns.

Each confirmed passed check adds its weight to the earned score. Each confirmed failed check adds its weight to the verifiable total but not the earned score. `Unknown` checks are ignored in the score because they mean the tool could not verify the result.

Weights:

- AI crawler permissions: 30
- `robots.txt`: 15
- `sitemap.xml`: 15
- Title: 15
- Meta Description: 10
- Schema: 10
- `llms.txt`: 5

Formula:

```text
Score = earned_weight / verifiable_weight * 100
```

`Unknown` checks are not included in `verifiable_weight`.

The report also shows:

- Passed Checks
- Failed Checks
- Unknown Checks

If more than 70% of all checks are `Unknown`, the app does not show `0/100` or `Critical Visibility Issues`. It shows:

```text
Status: Unable to Verify
Reason: Most checks could not be verified due to bot protection, HTTP restrictions, or crawler blocking.
```

For example:

- all major checks passed, only `llms.txt` missing = 95
- all AI crawlers blocked, other major checks passed = 70
- Schema and `llms.txt` missing, everything else passed = 85
- 0 passed, 0 failed, 12 unknown = Unable to Verify

This is intentionally simple. The goal is not perfect SEO scoring. The goal is to make the product idea easy to understand.

## How To Generate A Simple Report

1. Run the app locally.
2. Enter a website URL.
3. Click `Run Audit`.
4. Review the total score, status, summary, and Top 3 Fixes.
5. Copy the text from the `Copyable Report` box.
6. Paste it into an email, DM, Notion page, Google Doc, or customer feedback thread.

This lets you send a lightweight audit without building a full SaaS dashboard.

## Feedback Form

The app includes a `Give Feedback` link to a Tally form.

Use it to collect quick feedback when a report is useful, confusing, or wrong. This feedback helps improve the scoring model and report quality during market validation.

The app does not store feedback locally and does not use a database.

## Why Copyable Report Matters For Market Validation

The fastest way to validate this product is not to build accounts, billing, or automation.

The fastest way is to send useful reports to real website owners and see whether they care enough to respond, ask follow-up questions, or pay for a deeper audit.

A copyable report helps because:

- it is easy to send to SaaS founders and indie hackers
- it makes the audit feel concrete instead of theoretical
- it lets SEO freelancers test whether clients understand the value
- it creates a manual sales workflow before any SaaS infrastructure exists
- it helps you learn which issues people actually care about

## How This Could Become A SaaS Later

This MVP could become a SaaS by adding:

1. Scheduled monitoring
   - Re-check websites weekly or daily.
   - Alert users when `robots.txt`, `sitemap.xml`, `llms.txt`, schema, or metadata changes.

2. AI crawler checks
   - Check whether common AI crawlers like GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, and Googlebot are allowed or blocked.

3. Better reports
   - Generate shareable reports for founders, marketers, and SEO freelancers.
   - Include prioritized fixes and examples.

4. Competitor comparison
   - Compare a site against competitors for AI-readiness signals.

5. Prompt-based visibility checks
   - Test whether AI search tools mention the product for relevant questions.

6. Paid plans
   - Free: one-time basic scan.
   - Starter: monthly monitoring for one site.
   - Agency: multiple client sites and white-label reports.

The important point: the SaaS should not start as a large dashboard. It should start as a small tool that answers one valuable question:

Can AI systems and search engines clearly find, understand, and describe this website?

## Simple Explanations For Non-SEO Experts

### What is `robots.txt`?

`robots.txt` is like a front-door note for web crawlers.

It says: "You can look here, but please do not look there."

Search engines and some AI crawlers read this file before crawling a website. If it is configured badly, it can accidentally block useful crawlers.

### What is an AI crawler?

An AI crawler is a bot used by an AI company or AI product to fetch public web pages.

The crawler may be used for search, browsing, indexing, model-related systems, or product experiences. Different companies use different crawler names.

### What is GPTBot?

`GPTBot` is an OpenAI crawler name.

For this MVP, the important question is simple: does `robots.txt` allow or block `GPTBot` from accessing the public site?

### What is OAI-SearchBot?

`OAI-SearchBot` is another OpenAI crawler name associated with search-related crawling.

If a site wants to be visible in AI search experiences, it is useful to know whether this crawler is allowed or blocked.

### What is ChatGPT-User?

`ChatGPT-User` represents requests connected to user-driven ChatGPT browsing or retrieval behavior.

Blocking it may affect whether user-triggered AI browsing can access public pages.

### What is ClaudeBot?

`ClaudeBot` is an Anthropic crawler name.

If it is blocked in `robots.txt`, Claude-related systems may have less direct access to the site's public content.

### What is PerplexityBot?

`PerplexityBot` is a Perplexity crawler name.

Because Perplexity is an answer engine, blocking this crawler can matter for sites that want to be found or cited in Perplexity-style search experiences.

### What is Google-Extended?

`Google-Extended` is a Google control token used in `robots.txt`.

It is not the same as blocking normal Google Search indexing. It is related to whether site content can be used for certain Google AI-related systems.

### Why can `robots.txt` affect AI search visibility?

AI search systems need access to public pages before they can understand them well.

If `robots.txt` blocks an AI crawler, that crawler may not fetch the page directly. That does not always mean the site disappears from AI answers, but it can reduce direct machine access to the site's content.

For a SaaS website, this matters because AI systems need to understand pages like:

- homepage
- pricing
- docs
- changelog
- feature pages
- comparison pages
- FAQ pages

If these pages are blocked or hard to access, AI systems may rely on older, incomplete, or third-party information.

### What does Unknown mean?

`Unknown` means the tool could not verify the result.

It does not mean the website passed. It also does not mean the website failed.

Common reasons:

- SSL certificate verification failed
- the request timed out
- the site returned HTTP 403
- Cloudflare or bot protection blocked the request
- rate limiting blocked the request
- the domain could not be reached

In V0.3, `Unknown` is neutral in the score. It does not add points and does not remove points.

This matters because some websites use strong bot protection. For example, a site may block this local audit script with Cloudflare, rate limits, HTTP 403 responses, or crawler restrictions.

That tells us the audit could not complete. It does not prove the website has bad SEO, missing metadata, or poor AI search readiness.

When most checks are `Unknown`, the honest report status is `Unable to Verify`, not `Critical Visibility Issues`.

### What is `sitemap.xml`?

`sitemap.xml` is like a map of the website.

It lists important pages so crawlers can find them faster.

For a SaaS, this might include the homepage, pricing page, docs, blog posts, feature pages, and comparison pages.

### What is `llms.txt`?

`llms.txt` is an emerging file format for AI systems.

It is meant to give AI tools a clean summary of what a site is, what pages matter, and where useful content lives.

It is not guaranteed to improve rankings, but it is a simple way to make a site easier for AI systems to understand.

### What is Schema?

Schema is structured data added to a web page.

Normal text says:

```text
Acme is a project management app for freelancers.
```

Schema helps machines understand:

```text
This is a software product.
This is the company name.
This is the price.
These are FAQs.
```

It turns page content into clearer labels for search engines and AI systems.

### Why might AI search care about these things?

AI search systems need to answer questions. To do that well, they need to:

- find the website
- access the website
- understand what the website is about
- identify important pages
- extract reliable facts
- avoid guessing

`robots.txt`, `sitemap.xml`, `llms.txt`, title tags, meta descriptions, and schema all help with one or more of those jobs.

They do not guarantee that an AI system will recommend a website. But they reduce confusion and make the website easier for machines to process.
