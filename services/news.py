"""Adverse-news engine. Multi-source, deduplicated, scored.

Sources, in priority order:
 1. GDELT 2.0 DOC API     — multilingual, structured, can rate-limit
 2. Google News RSS       — English-bias but always works, no auth, polite
Both return a normalized article shape; we merge + dedupe by domain+title-stem.

Adverse-tone scoring: each article gets a +1/0 per matched keyword. Articles
with score >= 1 are flagged as adverse. The article list is always returned
in full (analyst sees everything), but the count of *adverse* articles drives
the rollup score.
"""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
from . import http

GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"

# An article is "adverse" only when it mentions BOTH:
#   (a) a safeguards TOPIC the project should be evaluated on, AND
#   (b) an ADVERSE-CLAIM verb/noun that frames the topic negatively.
# This kills false positives like "Project secures FPIC" (topic-only)
# or "Mining company sued" (claim-only, wrong subject).
TOPIC_KEYWORDS = [
    # Indigenous / community
    "indigenous", "fpic", "consent", "land rights", "tribal", "first nations",
    "community", "displacement", "eviction", "smallholder",
    # Carbon integrity
    "credit", "credits", "offset", "offsets", "carbon", "redd",
    # Environmental
    "deforestation", "forest", "biodiversity", "permanence",
]

ADVERSE_CLAIM_KEYWORDS = [
    # Carbon integrity adverse
    "over-credit", "over-credits", "over-credited", "overcrediting", "overstated",
    "phantom", "junk", "greenwashing", "greenwash", "fraud", "scam", "scandal",
    "inflated", "bogus", "misleading", "withdrawn", "suspended", "delisted",
    # Legal adverse
    "lawsuit", "sue", "sued", "suing", "court", "ruling", "complaint", "injunction",
    "violation", "violated", "violating", "abuse", "abused", "abuses",
    "evicted", "evicting", "displaced", "displacing", "seized",
    # Investigative adverse
    "investigation", "investigated", "exposed", "exposes", "expose", "uncovered",
    "leaked", "alleges", "alleged", "denounce", "denounced", "criticised", "criticized",
    "reject", "rejected", "rejection", "without consent", "no consent",
]

# Domains that signal investigative/NGO sourcing (boost only when adverse-claim present)
NGO_DOMAINS = [
    "mongabay.com", "carbonmarketwatch.org", "survivalinternational.org",
    "forestpeoples.org", "newyorker.com", "theguardian.com", "intercontinentalcry",
    "climateinvestigationscenter", "bloomberg.com", "ft.com", "reuters.com",
    "climatehome", "rainforest-alliance", "oxfam",
]


def _adverse_score(title: str | None, domain: str | None) -> int:
    """Score is non-zero only if BOTH a topic and an adverse-claim term appear.
    Prevents 'Project secures FPIC' from scoring like 'Project violates FPIC'.
    """
    if not title:
        return 0
    t = title.lower()
    has_topic = any(kw in t for kw in TOPIC_KEYWORDS)
    claim_hits = sum(1 for kw in ADVERSE_CLAIM_KEYWORDS if kw in t)
    if not has_topic or claim_hits == 0:
        return 0
    score = claim_hits
    if domain:
        d = domain.lower()
        if any(ng in d for ng in NGO_DOMAINS):
            score += 1
    return score


def _normalize_article(title: str, url: str, domain: str | None, language: str | None,
                       seendate: str | None, country: str | None, source: str) -> dict:
    return {
        "title": title.strip() if title else "",
        "url": url,
        "domain": domain,
        "language": language,
        "seendate": seendate,
        "country": country,
        "source": source,
        "adverse_score": _adverse_score(title, domain),
    }


def _dedupe(articles: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for a in articles:
        title = (a.get("title") or "").lower()
        # First 60 chars of normalized title
        key_title = re.sub(r"[^a-z0-9]+", "", title)[:60]
        domain = (a.get("domain") or "").lower()
        key = (key_title, domain)
        if not key_title or key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def _via_gdelt(query: str, timespan: str, max_records: int) -> list[dict]:
    res = http.get_json(GDELT_DOC, params={
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": str(max_records),
        "timespan": timespan,
        "sort": "datedesc",
    }, retries=0, timeout=4.0)
    if not res.get("ok") or not res.get("data"):
        return []
    arts = (res["data"] or {}).get("articles") or []
    return [
        _normalize_article(
            title=a.get("title", ""),
            url=a.get("url"),
            domain=a.get("domain"),
            language=a.get("language"),
            seendate=a.get("seendate"),
            country=a.get("sourcecountry"),
            source="gdelt",
        )
        for a in arts
    ]


def _via_google_news(query: str, max_records: int) -> list[dict]:
    res = http.get_text(GOOGLE_NEWS_RSS, params={
        "q": query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }, retries=0, timeout=5.0)
    if not res.get("ok") or not res.get("text"):
        return []
    try:
        root = ET.fromstring(res["text"])
    except ET.ParseError:
        return []
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        source_el = item.find("source")
        domain = None
        if source_el is not None:
            url_attr = source_el.get("url") or ""
            m = re.search(r"https?://([^/]+)", url_attr)
            domain = m.group(1) if m else None
        out.append(_normalize_article(
            title=title, url=link, domain=domain,
            language="en", seendate=pub, country=None, source="google-news",
        ))
        if len(out) >= max_records:
            break
    return out


# Tokens routinely tacked onto carbon-project names. Including them in the
# exact-phrase query kills matches because article titles rarely echo the
# full project name verbatim ("Wildlife Works Kasigau Corridor REDD+ Project"
# appears as "Wildlife Works Kasigau Corridor" in 90% of coverage).
_NAME_SUFFIX_TOKENS = {
    "redd+", "redd", "project", "initiative", "program", "programme",
    "conservation", "plantation", "reforestation", "afforestation",
    "carbon", "the", "and", "of", "a", "an",
}


def _build_query_variants(name: str, country: str | None) -> list[tuple[str, str]]:
    """Return a list of (gdelt_query, google_query) variants, broadest-last.
    Variants:
      1. Full quoted name + country
      2. Stripped name (suffixes like 'REDD+ / Project / Program' removed) + country
      3. Distinctive core (first 2-3 substantive words) + country
    Duplicates are deduplicated so we don't hit the same upstream twice.
    """
    name = (name or "").strip()
    if not name:
        return []

    def quoted(s: str) -> tuple[str, str]:
        q = f'"{s}"'
        g = f'{q} {country}' if country else q
        return g, q

    words = name.split()
    stripped_words = [w for w in words if w.lower().strip(",.+:;") not in _NAME_SUFFIX_TOKENS]
    stripped = " ".join(stripped_words).strip()
    if len(words) >= 4:
        core = " ".join(words[:3]).strip()
    elif len(words) >= 3:
        core = " ".join(words[:2]).strip()
    else:
        core = ""

    variants: list[tuple[str, str]] = []
    seen_google = set()
    for s in (name, stripped, core):
        if not s or len(s) < 3:
            continue
        g_q, n_q = quoted(s)
        if n_q in seen_google:
            continue
        seen_google.add(n_q)
        variants.append((g_q, n_q))
    return variants


def adverse_news(project_name: str, country: str | None = None,
                 timespan: str = "24months", max_records: int = 12,
                 min_articles_target: int = 3) -> dict:
    """Fan out to GDELT + Google News across cascading query variants.

    Strategy: try the exact-name variant first. If fewer than `min_articles_target`
    deduplicated articles come back, fall back to a stripped-suffix variant,
    then a distinctive-core variant. Stops early once the target is met. This
    attacks the v0.3 blind-test miss where exact-name searches on long project
    names returned 0 results despite known coverage existing in major outlets.

    Returns:
      {
        ok: True,
        articles: [...],
        adverse_count: int,
        total: int,
        sources_used: [...],
        query_variants_used: [...],   # which name forms actually fired
      }
    """
    if not project_name:
        return {"ok": False, "articles": [], "adverse_count": 0, "total": 0,
                "sources_used": [], "query_variants_used": [], "error": "empty project name"}

    variants = _build_query_variants(project_name, country)
    sources_used: list[str] = []
    variants_used: list[str] = []
    articles: list[dict] = []

    for gdelt_query, google_query in variants:
        g = _via_gdelt(gdelt_query, timespan, max_records)
        if g:
            if "gdelt" not in sources_used:
                sources_used.append("gdelt")
            articles.extend(g)
        n = _via_google_news(google_query, max_records)
        if n:
            if "google-news" not in sources_used:
                sources_used.append("google-news")
            articles.extend(n)
        if g or n:
            variants_used.append(google_query)
        # Dedupe in-flight so the stop condition tracks unique articles.
        articles = _dedupe(articles)
        if len(articles) >= min_articles_target:
            break

    articles.sort(key=lambda a: (-a.get("adverse_score", 0), a.get("seendate") or ""), reverse=False)
    articles.sort(key=lambda a: (-a.get("adverse_score", 0)))

    adverse_count = sum(1 for a in articles if a.get("adverse_score", 0) >= 1)

    return {
        "ok": True,
        "articles": articles[:max_records],
        "adverse_count": adverse_count,
        "total": len(articles),
        "sources_used": sources_used,
        "query_variants_used": variants_used,
    }
