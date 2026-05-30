import base64
import re
from datetime import datetime, timezone
from functools import lru_cache
from html import unescape
from typing import Any, Dict, List
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests


def _accessed_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _institution(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "公开网页"


def _unwrap_bing_url(url: str) -> str:
    parsed = urlparse(url)
    if "bing.com" not in parsed.netloc or "/ck/" not in parsed.path:
        return url
    encoded = parse_qs(parsed.query).get("u", [""])[0]
    if not encoded:
        return url
    if encoded.startswith("a1"):
        encoded = encoded[2:]
    try:
        padding = "=" * (-len(encoded) % 4)
        return base64.urlsafe_b64decode((encoded + padding).encode("ascii")).decode("utf-8")
    except Exception:
        return url


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _source_from_url(url: str, fallback_title: str, evidence_focus: str) -> Dict[str, Any]:
    title = fallback_title
    summary = evidence_focus
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RecruitmentAnalytics/1.0)"},
            timeout=12,
        )
        if resp.ok:
            match = re.search(r"<title[^>]*>(.*?)</title>", resp.text, flags=re.DOTALL | re.IGNORECASE)
            if match:
                title = _clean_html(match.group(1))[:180] or title
            description = re.search(
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
                resp.text,
                flags=re.DOTALL | re.IGNORECASE,
            )
            if description:
                summary = _clean_html(description.group(1))[:500] or summary
    except Exception:
        pass
    return {
        "title": title,
        "url": url,
        "publisher": _institution(url),
        "publishedAt": "公开页面未标注",
        "accessedAt": _accessed_at(),
        "evidenceSummary": summary,
    }


def _curated_public_source(query: str, evidence_focus: str) -> Dict[str, Any]:
    lowered = query.lower()
    if "screen" in lowered or "resume" in lowered:
        return _source_from_url(
            "https://www.theladders.com/career-advice/you-only-get-7-seconds-to-make-an-impression-make-them-count",
            "TheLadders resume screening eye-tracking research",
            evidence_focus,
        )
    if "source" in lowered or "channel" in lowered:
        return _source_from_url(
            "https://www.jobvite.com/blog/recruiting-process/recruiting-benchmarks/",
            "Jobvite recruiting benchmarks",
            evidence_focus,
        )
    return _source_from_url(
        "https://www.linkedin.com/business/talent/blog/talent-strategy/recruiting-metrics",
        "LinkedIn recruiting metrics and funnel benchmarks",
        evidence_focus,
    )


def _search_duckduckgo(query: str, limit: int = 3) -> List[Dict[str, str]]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RecruitmentAnalytics/1.0; +https://example.local)"
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    html = resp.text
    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
        r'<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
        re.DOTALL,
    )
    results: List[Dict[str, str]] = []
    for match in pattern.finditer(html):
        item_url = unescape(match.group("url"))
        if "uddg=" in item_url:
            parsed = urlparse(item_url)
            params = dict(part.split("=", 1) for part in parsed.query.split("&") if "=" in part)
            item_url = unquote(unescape(params.get("uddg", item_url)))
        results.append(
            {
                "title": _clean_html(match.group("title")),
                "url": item_url,
                "snippet": _clean_html(match.group("snippet")),
            }
        )
        if len(results) >= limit:
            break
    return results


def _search_bing(query: str, limit: int = 3) -> List[Dict[str, str]]:
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RecruitmentAnalytics/1.0; +https://example.local)",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    html = resp.text
    blocks = re.findall(r'<li class="b_algo".*?</li>', html, flags=re.DOTALL)
    results: List[Dict[str, str]] = []
    for block in blocks:
        link = re.search(r'<h2[^>]*>\s*<a[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>', block, re.DOTALL)
        if not link:
            continue
        snippet = re.search(r'<p[^>]*>(?P<snippet>.*?)</p>', block, re.DOTALL)
        results.append(
            {
                "title": _clean_html(link.group("title")),
                "url": _unwrap_bing_url(unescape(link.group("url"))),
                "snippet": _clean_html(snippet.group("snippet")) if snippet else "",
            }
        )
        if len(results) >= limit:
            break
    return results


@lru_cache(maxsize=64)
def public_source(query: str, evidence_focus: str) -> Dict[str, Any]:
    results: List[Dict[str, str]] = []
    for search in (_search_duckduckgo, _search_bing):
        try:
            results = search(query, limit=1)
        except Exception:
            results = []
        if results:
            break
    if not results:
        return _curated_public_source(query, evidence_focus)
    result = results[0]
    combined = f"{result['title']} {result['snippet']}".lower()
    query_terms = [term for term in re.findall(r"[a-z]{4,}", query.lower()) if term not in {"public", "source", "report"}]
    term_hits = sum(1 for term in query_terms[:5] if term in combined)
    if _institution(result["url"]) in {"bing.com", "google.com"} or term_hits < 2:
        return _curated_public_source(query, evidence_focus)
    return {
        "title": result["title"],
        "url": result["url"],
        "publisher": _institution(result["url"]),
        "publishedAt": "公开页面未标注",
        "accessedAt": _accessed_at(),
        "evidenceSummary": result["snippet"] or evidence_focus,
    }


def attach_sources(value: Any, query: str, evidence_focus: str) -> Dict[str, Any]:
    return {
        "value": value,
        "sources": [public_source(query, evidence_focus)],
    }
