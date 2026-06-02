import socket
import ssl
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import streamlit as st

try:
    import certifi
except ImportError:
    try:
        from pip._vendor import certifi
    except ImportError:
        certifi = None


# This MVP intentionally stays small:
# - no database
# - no accounts
# - no payment
# - no background jobs
# - no SaaS dashboard
#
# It only answers one product question:
# "Can this website be understood and discovered by search engines and AI tools?"


REQUEST_TIMEOUT_SECONDS = 10
USER_AGENT = (
    "Mozilla/5.0 (compatible; AI-Search-Visibility-Auditor-MVP/0.3; "
    "+https://localhost)"
)

CHECK_PRIORITY = {
    "Homepage Fetch": 0,
    "GPTBot": 1,
    "OAI-SearchBot": 2,
    "ClaudeBot": 3,
    "PerplexityBot": 4,
    "robots.txt": 5,
    "sitemap.xml": 6,
    "Title": 7,
    "Meta Description": 8,
    "Schema Markup": 9,
    "llms.txt": 10,
}

AI_CRAWLERS = [
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "PerplexityBot",
    "Google-Extended",
]

CHECK_WEIGHTS = {
    "robots.txt": 15,
    "sitemap.xml": 15,
    "Title": 15,
    "Meta Description": 10,
    "Schema Markup": 10,
    "llms.txt": 5,
}

AI_CRAWLER_TOTAL_WEIGHT = 30
AI_CRAWLER_WEIGHT = AI_CRAWLER_TOTAL_WEIGHT / len(AI_CRAWLERS)


class HomepageParser(HTMLParser):
    """Extract the few HTML signals this MVP needs from a homepage."""

    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title_parts = []
        self.meta_description = ""
        self.has_schema_markup = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = {name.lower(): value for name, value in attrs if name}

        if tag.lower() == "title":
            self.in_title = True

        # Standard meta description:
        # <meta name="description" content="...">
        if tag.lower() == "meta":
            name = (attrs_dict.get("name") or "").lower()
            content = attrs_dict.get("content") or ""
            if name == "description" and content.strip():
                self.meta_description = content.strip()

        # JSON-LD is the most common schema format:
        # <script type="application/ld+json">...</script>
        if tag.lower() == "script":
            script_type = (attrs_dict.get("type") or "").lower()
            if "application/ld+json" in script_type:
                self.has_schema_markup = True

        # Microdata is another schema format:
        # <div itemscope itemtype="https://schema.org/Product">
        if "itemscope" in attrs_dict or "itemtype" in attrs_dict or "itemprop" in attrs_dict:
            self.has_schema_markup = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self):
        return " ".join(part.strip() for part in self.title_parts if part.strip()).strip()


def normalize_url(raw_url):
    """Accept example.com or https://example.com and return a clean base URL."""
    url = raw_url.strip()
    if not url:
        return ""

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)
    if not parsed.netloc:
        return ""

    return f"{parsed.scheme}://{parsed.netloc}"


def fetch_url(url):
    """Fetch a URL and return a simple response dictionary.

    urllib is used instead of extra dependencies to keep this MVP easy to run.
    SSL verification stays enabled. If certifi is installed, its CA bundle is
    used because some local Python installs do not ship a complete trust store.
    """
    request = Request(url, headers={"User-Agent": USER_AGENT})
    context = create_ssl_context()

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS, context=context) as response:
            raw_body = response.read(1_000_000)
            charset = response.headers.get_content_charset() or "utf-8"
            body = raw_body.decode(charset, errors="replace")
            return {
                "ok": 200 <= response.status < 400,
                "status": response.status,
                "body": body,
                "error": "",
                "error_type": "",
            }
    except HTTPError as error:
        error_type = "404" if error.code == 404 else "HTTP Error"
        return {
            "ok": False,
            "status": error.code,
            "body": "",
            "error": f"{error_type}: HTTP {error.code}",
            "error_type": error_type,
        }
    except TimeoutError as error:
        return {
            "ok": False,
            "status": None,
            "body": "",
            "error": f"Timeout: {error}",
            "error_type": "Timeout",
        }
    except URLError as error:
        error_type = classify_url_error(error)
        return {
            "ok": False,
            "status": None,
            "body": "",
            "error": f"{error_type}: {error.reason}",
            "error_type": error_type,
        }


def create_ssl_context():
    """Create a verifying SSL context without disabling certificate checks."""
    if certifi:
        return ssl.create_default_context(cafile=certifi.where())

    return ssl.create_default_context()


def classify_url_error(error):
    """Turn low-level urllib errors into product-level error labels."""
    reason = error.reason

    if isinstance(reason, ssl.SSLError) or "CERTIFICATE_VERIFY_FAILED" in str(reason):
        return "SSL Error"

    if isinstance(reason, socket.timeout) or "timed out" in str(reason).lower():
        return "Timeout"

    return "Connection Error"


def make_result(name, passed, issue, suggestion, evidence, status=None):
    """Create one check result in a consistent shape for UI and scoring."""
    if status is None:
        status = "passed" if passed else "failed"

    return {
        "name": name,
        "passed": passed,
        "status": status,
        "issue": issue,
        "suggestion": suggestion,
        "evidence": evidence,
    }


def check_static_file(base_url, path, label, issue, suggestion):
    """Check whether a common website file exists at the expected root path."""
    target_url = urljoin(base_url, path)
    response = fetch_url(target_url)
    return build_static_file_result(target_url, response, label, issue, suggestion)


def build_static_file_result(target_url, response, label, issue, suggestion):
    """Convert a fetched static-file response into one report result."""
    if response["ok"]:
        return make_result(
            label,
            True,
            "No obvious issue found.",
            "Keep this file updated as your site changes.",
            f"Found at {target_url} with status {response['status']}.",
        )

    error_type = response["error_type"]
    evidence = response["error"] or f"Status {response['status']}"

    if error_type == "404":
        result_issue = issue
        result_suggestion = suggestion
        result_status = "failed"
    elif error_type == "SSL Error":
        result_issue = f"{label} could not be checked because SSL certificate verification failed."
        result_suggestion = "Verify the site certificate chain and make sure this Python environment has an up-to-date CA certificate bundle."
        result_status = "unknown"
    elif error_type == "Timeout":
        result_issue = f"{label} could not be checked because the request timed out."
        result_suggestion = "Try again later or check whether the site is slow, blocking crawlers, or having network issues."
        result_status = "unknown"
    elif error_type == "Connection Error":
        result_issue = f"{label} could not be checked because the connection failed."
        result_suggestion = "Check whether the domain is reachable and whether a firewall, DNS issue, or hosting problem is blocking access."
        result_status = "unknown"
    else:
        result_issue = f"{label} could not be confirmed because the server returned an HTTP error."
        result_suggestion = "Check the file URL in a browser. If it should be public, make sure the server allows crawlers to access it."
        result_status = "unknown"

    return make_result(
        label,
        False,
        result_issue,
        result_suggestion,
        f"Checked {target_url}: {evidence}.",
        result_status,
    )


def get_robots_txt(base_url):
    """Fetch robots.txt once so file existence and crawler checks share evidence."""
    target_url = urljoin(base_url, "/robots.txt")
    return target_url, fetch_url(target_url)


def parse_robots_groups(robots_text):
    """Parse enough of robots.txt for root-path AI crawler checks.

    This intentionally implements a small, readable subset of the robots rules:
    User-agent, Allow, and Disallow. It is enough for V0.3 report validation.
    """
    groups = []
    current_agents = []
    current_rules = []

    for raw_line in robots_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue

        field, value = line.split(":", 1)
        field = field.strip().lower()
        value = value.strip()

        if field == "user-agent":
            if current_rules:
                groups.append({"agents": current_agents, "rules": current_rules})
                current_agents = []
                current_rules = []
            current_agents.append(value.lower())
        elif field in {"allow", "disallow"} and current_agents:
            if not value:
                continue
            current_rules.append({"type": field, "path": value})

    if current_agents or current_rules:
        groups.append({"agents": current_agents, "rules": current_rules})

    return groups


def evaluate_crawler_access(robots_text, crawler):
    """Return Allowed, Blocked, or Unknown for a crawler at the homepage path."""
    groups = parse_robots_groups(robots_text)
    crawler_name = crawler.lower()
    matching_rules = []

    for group in groups:
        agents = group["agents"]
        if crawler_name in agents or "*" in agents:
            matching_rules.extend(group["rules"])

    if not matching_rules:
        return "Allowed", "No matching robots.txt rule blocks this crawler."

    best_rule = None
    for rule in matching_rules:
        rule_path = rule["path"]
        if rule_path == "" or "/".startswith(rule_path):
            if best_rule is None or len(rule_path) > len(best_rule["path"]):
                best_rule = rule
            elif best_rule and len(rule_path) == len(best_rule["path"]):
                if rule["type"] == "allow" and best_rule["type"] == "disallow":
                    best_rule = rule

    if not best_rule:
        return "Allowed", "No matching robots.txt rule applies to the homepage."

    if best_rule["type"] == "disallow":
        return "Blocked", f"robots.txt has Disallow: {best_rule['path']} for this crawler."

    return "Allowed", f"robots.txt has Allow: {best_rule['path']} for this crawler."


def build_ai_crawler_results(robots_response):
    """Create one result per AI crawler from robots.txt."""
    results = []

    if not robots_response["ok"]:
        error_type = robots_response["error_type"]
        evidence = robots_response["error"] or f"Status {robots_response['status']}"

        for crawler in AI_CRAWLERS:
            if error_type == "404":
                results.append(
                    make_result(
                        crawler,
                        True,
                        "No robots.txt file was found, so no crawler-specific block was detected.",
                        "Add robots.txt if you want explicit crawler rules.",
                        "robots.txt returned 404. Crawlers are generally allowed when robots.txt is missing.",
                    )
                )
            else:
                results.append(
                    make_result(
                        crawler,
                        False,
                        f"Unable to verify {crawler} because robots.txt could not be checked.",
                        "Retry later or check whether bot protection, SSL, DNS, or hosting issues are blocking robots.txt.",
                        evidence,
                        "unknown",
                    )
                )
        return results

    for crawler in AI_CRAWLERS:
        access_status, reason = evaluate_crawler_access(robots_response["body"], crawler)

        if access_status == "Blocked":
            results.append(
                make_result(
                    crawler,
                    False,
                    f"{crawler} is blocked by robots.txt.",
                    f"Review robots.txt and allow {crawler} if you want this AI crawler to access public pages.",
                    reason,
                )
            )
        else:
            results.append(
                make_result(
                    crawler,
                    True,
                    "No crawler block detected.",
                    "Keep robots.txt aligned with your AI search visibility strategy.",
                    reason,
                )
            )

    return results


def parse_homepage(base_url):
    """Fetch and parse the homepage for title, meta description, and schema."""
    response = fetch_url(base_url)
    parser = HomepageParser()

    if response["ok"]:
        parser.feed(response["body"])

    return response, parser


def audit_site(raw_url):
    """Run the MVP checks and calculate a simple 0-100 score."""
    base_url = normalize_url(raw_url)
    if not base_url:
        return None, []

    results = []
    robots_url, robots_response = get_robots_txt(base_url)

    results.append(
        build_static_file_result(
            robots_url,
            robots_response,
            "robots.txt",
            "robots.txt was not found at the website root.",
            "Add a robots.txt file so crawlers can clearly understand which areas are allowed or blocked.",
        )
    )

    results.extend(build_ai_crawler_results(robots_response))

    results.append(
        check_static_file(
            base_url,
            "/sitemap.xml",
            "sitemap.xml",
            "sitemap.xml was not found at the website root.",
            "Add a sitemap.xml file listing your important pages, then submit it to Google Search Console.",
        )
    )

    results.append(
        check_static_file(
            base_url,
            "/llms.txt",
            "llms.txt",
            "llms.txt was not found at the website root.",
            "Consider adding llms.txt as an optional AI-readiness enhancement that summarizes your site for AI systems.",
        )
    )

    homepage_response, parser = parse_homepage(base_url)

    if not homepage_response["ok"]:
        evidence = homepage_response["error"] or f"Status {homepage_response['status']}"
        homepage_status = "failed" if homepage_response["error_type"] == "404" else "unknown"
        homepage_issue = "The homepage could not be fetched, so this check could not be verified."
        homepage_suggestion = "Make sure the homepage loads for normal HTTP crawlers."
        results.extend(
            [
                make_result(
                    "Title",
                    False,
                    homepage_issue,
                    homepage_suggestion,
                    evidence,
                    homepage_status,
                ),
                make_result(
                    "Meta Description",
                    False,
                    homepage_issue,
                    homepage_suggestion,
                    evidence,
                    homepage_status,
                ),
                make_result(
                    "Schema Markup",
                    False,
                    homepage_issue,
                    homepage_suggestion,
                    evidence,
                    homepage_status,
                ),
            ]
        )
        return base_url, results

    results.append(
        make_result(
            "Title",
            bool(parser.title),
            "The homepage does not appear to have a title tag.",
            "Add a short, clear title that explains the product, brand, and main use case.",
            parser.title or "No title tag found.",
        )
    )

    results.append(
        make_result(
            "Meta Description",
            bool(parser.meta_description),
            "The homepage does not appear to have a meta description.",
            "Add a concise meta description that explains what the site does and who it is for.",
            parser.meta_description or "No meta description found.",
        )
    )

    results.append(
        make_result(
            "Schema Markup",
            parser.has_schema_markup,
            "No schema detected in static homepage HTML.",
            "Add structured data such as Organization, SoftwareApplication, Product, FAQ, or Article schema when relevant. This check only evaluates schema visible in the static homepage HTML and may not detect dynamically rendered structured data.",
            "Schema markup detected." if parser.has_schema_markup else "No schema detected in static homepage HTML.",
        )
    )

    return base_url, results


def calculate_score(results):
    """Passed checks add points; failed checks remove points; unknown is neutral."""
    earned_weight = 0
    verifiable_weight = 0

    for result in results:
        if result.get("status") not in {"passed", "failed"}:
            continue

        weight = get_result_weight(result)
        verifiable_weight += weight

        if result.get("status") == "passed":
            earned_weight += weight

    if verifiable_weight == 0:
        return 0

    return round((earned_weight / verifiable_weight) * 100)


def get_result_weight(result):
    """Return the scoring weight for a check result."""
    if result["name"] in AI_CRAWLERS:
        return AI_CRAWLER_WEIGHT

    return CHECK_WEIGHTS.get(result["name"], 0)


def get_check_counts(results):
    """Count passed, failed, and unknown checks for report transparency."""
    return {
        "passed": sum(1 for result in results if result.get("status") == "passed"),
        "failed": sum(1 for result in results if result.get("status") == "failed"),
        "unknown": sum(1 for result in results if result.get("status") == "unknown"),
        "total": len(results),
    }


def is_unable_to_verify(results):
    """If most checks are unknown, the audit result itself is inconclusive."""
    counts = get_check_counts(results)
    if counts["total"] == 0:
        return False

    return counts["unknown"] / counts["total"] > 0.7


def get_score_display(score, results):
    """Avoid showing misleading 0/100 scores for mostly unknown audits."""
    if is_unable_to_verify(results):
        return "Unable to Verify"

    return f"{score}/100"


def get_overall_status(score, results=None):
    """Map the numeric score to a founder-friendly report status."""
    if results is not None and is_unable_to_verify(results):
        return "Unable to Verify"

    if score >= 80:
        return "Ready for AI Search"

    if score >= 50:
        return "Needs Optimization"

    return "Critical Visibility Issues"


def get_result_state(result):
    """Classify each check as Passed, Needs Work, Error, or Unknown."""
    if result.get("status") == "passed":
        return "Passed"

    if result.get("status") == "unknown":
        return "Unknown"

    if result.get("status") == "failed":
        return "Needs Work"

    issue = result["issue"].lower()
    evidence = result["evidence"].lower()
    error_signals = [
        "ssl error",
        "timeout",
        "connection error",
        "http error",
        "could not be checked",
        "could not be confirmed",
        "could not be fetched",
    ]

    if any(signal in issue or signal in evidence for signal in error_signals):
        return "Error"

    return "Needs Work"


def homepage_fetch_failed(results):
    """Detect one shared homepage fetch problem instead of three duplicate fixes."""
    homepage_checks = {"Title", "Meta Description", "Schema Markup"}
    failed_homepage_checks = [
        result
        for result in results
        if result["name"] in homepage_checks and get_result_state(result) == "Unknown"
    ]
    return len(failed_homepage_checks) == len(homepage_checks)


def get_top_fixes(results):
    """Pick the three most important fixes using a fixed product priority."""
    if is_unable_to_verify(results):
        return []

    fixes = []

    if homepage_fetch_failed(results):
        first_homepage_error = next(
            result
            for result in results
            if result["name"] in {"Title", "Meta Description", "Schema Markup"}
        )
        fixes.append(
            {
                "name": "Homepage Fetch",
                "message": "Homepage could not be fetched or verified",
                "suggestion": first_homepage_error["suggestion"],
                "priority": CHECK_PRIORITY["Homepage Fetch"],
            }
        )

    for result in results:
        if result.get("status") != "failed":
            continue

        if homepage_fetch_failed(results) and result["name"] in {"Title", "Meta Description", "Schema Markup"}:
            continue

        message = get_fix_message(result)
        fixes.append(
            {
                "name": result["name"],
                "message": message,
                "suggestion": result["suggestion"],
                "priority": CHECK_PRIORITY.get(result["name"], 99),
            }
        )

    fixes.sort(key=lambda item: item["priority"])
    return fixes[:3]


def get_fix_message(result):
    """Turn a failed check into a customer-friendly priority line."""
    name = result["name"]

    if name in AI_CRAWLERS:
        return f"{name} is blocked by robots.txt"

    if name == "robots.txt":
        return "No robots.txt found"

    if name == "sitemap.xml":
        return "No sitemap.xml found"

    if name == "Title":
        return "Missing homepage title"

    if name == "Meta Description":
        return "Missing meta description"

    if name == "Schema Markup":
        return "Missing FAQ, Software, Product, or Organization schema"

    if name == "llms.txt":
        return "No llms.txt found"

    return result["issue"]


def build_summary(base_url, score, status, results, top_fixes):
    """Create a short rules-based English summary without using an AI API."""
    counts = get_check_counts(results)
    failed_names = [result["name"] for result in results if result.get("status") == "failed"]
    unknown_names = [result["name"] for result in results if result.get("status") == "unknown"]
    score_display = get_score_display(score, results)

    if is_unable_to_verify(results):
        sentences = [
            f"{base_url} could not be reliably audited.",
            "Most checks could not be verified due to bot protection, HTTP restrictions, or crawler blocking.",
            f"Passed Checks: {counts['passed']}. Failed Checks: {counts['failed']}. Unknown Checks: {counts['unknown']}.",
            "Confirmed Problems: "
            + (", ".join(failed_names) if failed_names else "None found in the checks that completed.")
            + ("." if failed_names else ""),
            "Unable To Verify: " + ", ".join(unknown_names) + ".",
        ]
        return " ".join(sentences)

    sentences = [
        f"{base_url} is currently classified as '{status}' with a score of {score_display}.",
        f"Passed Checks: {counts['passed']}. Failed Checks: {counts['failed']}. Unknown Checks: {counts['unknown']}.",
    ]

    if failed_names:
        sentences.append("Confirmed Problems: " + ", ".join(failed_names) + ".")
    else:
        sentences.append("Confirmed Problems: None found in the checks that completed.")

    if unknown_names:
        sentences.append("Unable To Verify: " + ", ".join(unknown_names) + ".")

    if top_fixes:
        fix_names = ", ".join(fix["message"] for fix in top_fixes)
        sentences.append(f"The highest-priority fixes are: {fix_names}.")

    sentences.append(
        "These checks do not guarantee AI search visibility, but they reduce basic crawler and machine-understanding problems."
    )
    return " ".join(sentences)


def get_crawler_readiness(results):
    """Return the crawler readiness rows for display and reports."""
    readiness = []
    result_by_name = {result["name"]: result for result in results}

    for crawler in AI_CRAWLERS:
        result = result_by_name.get(crawler)
        if not result:
            readiness.append({"name": crawler, "status": "Unknown", "reason": "Not checked."})
            continue

        if result.get("status") == "passed":
            crawler_status = "Allowed"
        elif result.get("status") == "failed":
            crawler_status = "Blocked"
        else:
            crawler_status = "Unknown"

        readiness.append(
            {
                "name": crawler,
                "status": crawler_status,
                "reason": result["evidence"],
            }
        )

    return readiness


def build_crawler_summary(crawler_readiness):
    """Summarize AI crawler access in plain English."""
    blocked = [item["name"] for item in crawler_readiness if item["status"] == "Blocked"]
    allowed = [item["name"] for item in crawler_readiness if item["status"] == "Allowed"]
    unknown = [item["name"] for item in crawler_readiness if item["status"] == "Unknown"]

    if blocked and allowed:
        first_sentence = "Most major AI crawlers can access this website." if len(allowed) > len(blocked) else "Some major AI crawlers may be blocked from this website."
        second_sentence = "However, " + ", ".join(blocked) + " appear to be blocked."
    elif blocked:
        first_sentence = "Major AI crawlers appear to be blocked from this website."
        second_sentence = "Blocked crawlers: " + ", ".join(blocked) + "."
    elif allowed:
        first_sentence = "Major AI crawlers appear to be allowed by robots.txt."
        second_sentence = "No crawler-specific block was detected in the current robots.txt check."
    else:
        first_sentence = "AI crawler readiness could not be verified."
        second_sentence = "robots.txt was unavailable or blocked during this audit."

    if unknown:
        second_sentence += " Unable to verify: " + ", ".join(unknown) + "."

    return f"{first_sentence} {second_sentence}"


def build_copyable_report(base_url, score, status, results, crawler_readiness, top_fixes, summary):
    """Build a plain-text report that can be pasted into email, DMs, or docs."""
    score_display = get_score_display(score, results)
    counts = get_check_counts(results)
    crawler_text = "\n".join(
        f"{item['name']}: {item['status']}" for item in crawler_readiness
    )

    if top_fixes:
        fixes_text = "\n".join(
            f"{index}. {fix['message']}"
            for index, fix in enumerate(top_fixes, start=1)
        )
    else:
        fixes_text = "No high-priority fixes found in the current basic checks."

    return (
        "AI Search Visibility Audit\n"
        "\n"
        f"URL: {base_url}\n"
        f"Total Score: {score_display}\n"
        f"Status: {status}\n"
        f"Passed Checks: {counts['passed']}\n"
        f"Failed Checks: {counts['failed']}\n"
        f"Unknown Checks: {counts['unknown']}\n\n"
        "AI Crawler Readiness\n"
        f"{crawler_text}\n\n"
        "Top Fixes\n"
        f"{fixes_text}\n\n"
        "Summary\n"
        f"{summary}"
    )


def render_result(result):
    """Render a single check in Streamlit."""
    state = get_result_state(result)

    with st.expander(f"{result['name']} - {state}", expanded=False):
        if state == "Passed":
            st.success(f"Passed: {result['name']}")
        elif state == "Unknown":
            st.info(f"Unknown: {result['name']}")
        else:
            st.warning(f"Needs Work: {result['name']}")

        st.write(f"**Status:** {state}")
        st.write(f"**Reason:** {result['issue']}")
        st.write(f"**Suggestion:** {result['suggestion']}")
        st.caption(f"Evidence: {result['evidence']}")


def inject_global_styles():
    """Add presentation-only CSS for a more polished single-page app."""
    st.markdown(
        """
        <style>
            :root {
                --card-bg: rgba(255, 255, 255, 0.045);
                --card-border: rgba(255, 255, 255, 0.13);
                --muted-text: rgba(255, 255, 255, 0.68);
                --strong-text: rgba(255, 255, 255, 0.96);
            }

            .block-container {
                max-width: 1120px;
                padding-top: 2.5rem;
                padding-bottom: 3rem;
            }

            .hero-card {
                border: 1px solid var(--card-border);
                border-radius: 16px;
                padding: clamp(1.25rem, 4vw, 2.25rem);
                background:
                    radial-gradient(circle at top left, rgba(80, 128, 255, 0.18), transparent 34%),
                    var(--card-bg);
                margin-bottom: 1rem;
            }

            .eyebrow {
                color: rgba(140, 170, 255, 0.95);
                font-weight: 700;
                font-size: 0.82rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.7rem;
            }

            .hero-title {
                color: var(--strong-text);
                font-weight: 800;
                font-size: clamp(2rem, 5vw, 3.4rem);
                line-height: 1.05;
                margin: 0 0 0.8rem 0;
            }

            .hero-subtitle {
                color: var(--muted-text);
                font-size: clamp(1rem, 2vw, 1.2rem);
                line-height: 1.6;
                max-width: 760px;
                margin-bottom: 1.1rem;
            }

            .support-row {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin: 0.7rem 0 0.25rem 0;
            }

            .pill {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 999px;
                color: rgba(255, 255, 255, 0.82);
                background: rgba(255, 255, 255, 0.055);
                padding: 0.34rem 0.7rem;
                font-size: 0.86rem;
            }

            .section-kicker {
                color: rgba(140, 170, 255, 0.92);
                font-size: 0.78rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-top: 0.2rem;
            }

            .section-title {
                color: var(--strong-text);
                font-size: clamp(1.35rem, 3vw, 1.9rem);
                font-weight: 760;
                margin: 0.1rem 0 0.35rem 0;
            }

            .section-copy {
                color: var(--muted-text);
                line-height: 1.55;
                margin-bottom: 1rem;
            }

            .card-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 0.9rem;
                margin: 1rem 0;
            }

            .info-card, .feedback-card {
                border: 1px solid var(--card-border);
                border-radius: 12px;
                padding: 1rem;
                background: var(--card-bg);
                min-width: 0;
            }

            .info-card-title {
                color: var(--strong-text);
                font-weight: 740;
                font-size: 1rem;
                margin-bottom: 0.45rem;
            }

            .info-card-body {
                color: var(--muted-text);
                line-height: 1.52;
                font-size: 0.94rem;
            }

            .example-value {
                color: var(--strong-text);
                font-size: clamp(1.35rem, 3vw, 2rem);
                line-height: 1.15;
                font-weight: 800;
                overflow-wrap: anywhere;
            }

            .result-title {
                color: var(--strong-text);
                font-size: clamp(1.35rem, 3vw, 2rem);
                font-weight: 760;
                line-height: 1.2;
                overflow-wrap: anywhere;
                margin-top: 0.4rem;
            }

            div[data-testid="stTextInput"] input {
                min-height: 3rem;
            }

            div[data-testid="stButton"] button,
            div[data-testid="stLinkButton"] a {
                border-radius: 8px;
                min-height: 2.8rem;
                font-weight: 700;
            }

            @media (max-width: 640px) {
                .block-container {
                    padding-left: 1rem;
                    padding-right: 1rem;
                    padding-top: 1.25rem;
                }

                .hero-card {
                    padding: 1.1rem;
                    border-radius: 12px;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_section_intro(kicker, title, copy):
    """Render a consistent section heading."""
    st.caption(kicker.upper())
    st.subheader(title)
    st.write(copy)


def render_summary_cards(score_display, status, counts):
    """Render audit summary cards without Streamlit metric truncation."""
    cards = [
        ("Total Score", score_display),
        ("Status", status),
        ("Passed Checks", counts["passed"]),
        ("Failed Checks", counts["failed"]),
        ("Unknown Checks", counts["unknown"]),
    ]
    card_columns = st.columns(5)
    for column, (label, value) in zip(card_columns, cards):
        with column:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"### {value}")


def render_feedback_cta():
    """Render a feedback call-to-action without storing data locally."""
    with st.container(border=True):
        st.caption("FEEDBACK")
        st.subheader("Help improve this tool")
        st.write(
            "If this audit was useful, confusing, or wrong, please leave quick feedback. "
            "It helps improve the scoring model and report quality."
        )
        st.link_button("Give Feedback", "https://tally.so/r/EkMEgo")


def render_homepage():
    """Render the public-facing single-page MVP experience."""
    with st.container(border=True):
        st.caption("FREE AI VISIBILITY AUDIT")
        st.title("AI Search Visibility Auditor")
        st.write(
            "Find out whether your website is ready to be understood, crawled, "
            "and referenced by AI systems."
        )
        st.write("Supports: **ChatGPT** | **Claude** | **Perplexity** | **Google AI**")

    url_input = st.text_input("Enter website URL", placeholder="https://example.com")
    run_audit = st.button("Run Free Audit", type="primary")
    result_container = st.container()

    if run_audit:
        with result_container:
            render_audit_report(url_input)

    st.divider()

    render_section_intro(
        "How it works",
        "From URL to audit in one pass",
        "Run a lightweight visibility check without accounts, installs, or setup.",
    )
    step_1, step_2, step_3 = st.columns(3)
    with step_1:
        with st.container(border=True):
            st.subheader("Step 1")
            st.write("Enter your website URL.")
    with step_2:
        with st.container(border=True):
            st.subheader("Step 2")
            st.write("We analyze AI crawler access and technical visibility signals.")
    with step_3:
        with st.container(border=True):
            st.subheader("Step 3")
            st.write("Receive a visibility score and detailed audit.")

    st.divider()

    render_section_intro(
        "What we check",
        "Crawler access plus technical visibility",
        "The report combines AI crawler permissions with basic signals that help machines discover and understand a website.",
    )
    crawler_col, technical_col = st.columns(2)
    with crawler_col:
        with st.container(border=True):
            st.subheader("AI Crawler Access")
            st.write("- GPTBot")
            st.write("- ClaudeBot")
            st.write("- PerplexityBot")
            st.write("- OAI-SearchBot")
            st.write("- ChatGPT-User")
            st.write("- Google-Extended")
    with technical_col:
        with st.container(border=True):
            st.subheader("Technical Visibility")
            st.write("- robots.txt")
            st.write("- sitemap.xml")
            st.write("- title tag")
            st.write("- meta description")
            st.write("- schema markup")
            st.write("- llms.txt")

    st.divider()

    render_section_intro(
        "Example results",
        "What a report can look like",
        "Static examples from real-world style test cases.",
    )
    examples = [
        ("OpenAI", "85"),
        ("Vercel", "100"),
        ("Replit", "70"),
        ("Midjourney", "Unable to Verify"),
    ]
    example_cols = st.columns(4)
    for column, (name, result) in zip(example_cols, examples):
        with column:
            with st.container(border=True):
                st.subheader(name)
                st.markdown(f"### {result}")

    st.divider()

    render_section_intro(
        "About the score",
        "Weighted, practical, and careful with uncertainty",
        "The score is based on AI crawler accessibility and technical visibility signals. Unknown checks are not treated as failures.",
    )

    st.divider()

    render_feedback_cta()

    st.divider()
    st.caption(
        "Built for SaaS founders, indie hackers, developers, and technical marketers."
    )

    return url_input, run_audit


def render_audit_report(url_input):
    """Render the existing audit report without changing the audit engine."""
    if not url_input.strip():
        st.warning("Please enter a website URL.")
    else:
        with st.spinner("Running audit..."):
            audited_url, audit_results = audit_site(url_input)

        if not audited_url:
            st.error("Please enter a valid website URL.")
        else:
            score = calculate_score(audit_results)
            status = get_overall_status(score, audit_results)
            score_display = get_score_display(score, audit_results)
            counts = get_check_counts(audit_results)
            top_fixes = get_top_fixes(audit_results)
            crawler_readiness = get_crawler_readiness(audit_results)
            crawler_summary = build_crawler_summary(crawler_readiness)
            summary = build_summary(audited_url, score, status, audit_results, top_fixes)
            summary = f"{summary} {crawler_summary}"
            copyable_report = build_copyable_report(
                audited_url, score, status, audit_results, crawler_readiness, top_fixes, summary
            )

            st.success("Audit completed. Results are shown below.")
            st.header(f"Audit Results for {audited_url}")

            render_summary_cards(score_display, status, counts)

            st.divider()

            if status == "Unable to Verify":
                st.info(
                    "Most checks could not be verified due to bot protection, HTTP restrictions, or crawler blocking."
                )
            elif score >= 80:
                st.info("Good foundation. The site has most basic visibility signals in place.")
            elif score >= 50:
                st.info("Some important signals are missing. Fixing them may improve crawler understanding.")
            else:
                st.info("Several basic visibility signals are missing. Start with robots.txt, sitemap.xml, and homepage metadata.")

            render_section_intro(
                "Summary",
                "Human-readable Summary",
                "A short interpretation of the current audit result.",
            )
            st.write(summary)

            render_section_intro(
                "Crawler readiness",
                "AI Crawler Readiness",
                "Whether major AI crawler user agents appear to be allowed, blocked, or unknown.",
            )
            crawler_columns = st.columns(3)
            for index, crawler in enumerate(crawler_readiness):
                with crawler_columns[index % 3]:
                    with st.container(border=True):
                        st.subheader(crawler["name"])
                        st.markdown(f"### {crawler['status']}")
            st.write(crawler_summary)

            render_section_intro(
                "Fix priority",
                "Top 3 Fixes",
                "The highest-impact confirmed issues from this audit.",
            )
            if top_fixes:
                for index, fix in enumerate(top_fixes, start=1):
                    with st.container(border=True):
                        st.write(f"**Priority {index}: {fix['message']}**")
                        st.caption(fix["suggestion"])
            else:
                st.write("No high-priority fixes found in the current basic checks.")

            render_section_intro(
                "Share",
                "Copyable Report",
                "Plain-text output for sending to a founder, developer, or marketer.",
            )
            st.text_area("Report", copyable_report, height=260)

            st.divider()

            render_section_intro(
                "Details",
                "Detailed Checks",
                "Open each item to see status, reason, suggestion, and evidence.",
            )
            for item in audit_results:
                render_result(item)

            render_feedback_cta()


st.set_page_config(page_title="AI Search Visibility Auditor")

inject_global_styles()
url_input, run_audit = render_homepage()
