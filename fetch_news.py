#!/usr/bin/env python3
"""Fetch yesterday's AI articles from outlets tracked journalists write for. Uses stdlib only."""

import datetime
import urllib.request
import xml.etree.ElementTree as ET
import re
import html as html_mod

# Outlets and the journalists who write for them
OUTLETS = {
    "The Guardian": {
        "journalists": ["Dan Milmo", "Alex Hern"],
        "feeds": [
            "https://www.theguardian.com/technology/artificialintelligenceai/rss",
            "https://www.theguardian.com/technology/rss",
        ],
    },
    "The New York Times": {
        "journalists": ["Kevin Roose", "Cade Metz", "Ezra Klein"],
        "feeds": [
            "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
        ],
    },
    "WIRED": {
        "journalists": ["Steven Levy", "Will Knight"],
        "feeds": [
            "https://www.wired.com/feed/category/artificial-intelligence/latest/rss",
            "https://www.wired.com/feed/rss",
        ],
    },
    "Bloomberg": {
        "journalists": ["Rachel Metz", "Dina Bass"],
        "feeds": [
            "https://feeds.bloomberg.com/technology/news.rss",
        ],
    },
    "The Atlantic": {
        "journalists": ["Karen Hao", "Matteo Wong"],
        "feeds": [
            "https://www.theatlantic.com/feed/all/",
        ],
    },
    "POLITICO": {
        "journalists": ["Melissa Heikkilä"],
        "feeds": [
            "https://rss.politico.com/politics-news.xml",
            "https://www.politico.eu/feed/",
        ],
    },
    "TIME": {
        "journalists": ["Billy Perrigo"],
        "feeds": [
            "https://time.com/feed/",
        ],
    },
    "Washington Post": {
        "journalists": ["Gerrit De Vynck"],
        "feeds": [
            "https://feeds.washingtonpost.com/rss/business/technology",
        ],
    },
    "BBC": {
        "journalists": ["Marc Cieslak"],
        "feeds": [
            "http://feeds.bbci.co.uk/news/technology/rss.xml",
        ],
    },
    "AP": {
        "journalists": ["Kelvin Chan"],
        "feeds": [
            "https://feeds.apnews.com/rss/apf-technology",
        ],
    },
    "The Economist": {
        "journalists": ["Kenneth Cukier"],
        "feeds": [
            "https://www.economist.com/science-and-technology/rss.xml",
            "https://www.economist.com/technology-quarterly/rss.xml",
        ],
    },
    "Financial Times": {
        "journalists": ["Madhumita Murgia"],
        "feeds": [
            "https://www.ft.com/rss/home/technology",
        ],
    },
}

AI_KEYWORDS = [
    "artificial intelligence", " ai ", "machine learning", "large language model",
    "llm", "openai", "anthropic", "deepmind", "chatgpt", "gpt", "gemini",
    "claude", "neural network", "generative ai", "ai safety", "ai regulation",
    "ai governance", "chatbot", "algorithm",
]

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_date(s):
    if not s:
        return None
    # RFC 822: Mon, 09 Jun 2026 08:00:00 +0000
    try:
        parts = s.strip().split()
        for i, p in enumerate(parts):
            if p[:3].lower() in MONTHS and i >= 1:
                day = int(parts[i - 1].rstrip(","))
                month = MONTHS[p[:3].lower()]
                year = int(parts[i + 1])
                return datetime.date(year, month, day)
    except Exception:
        pass
    # ISO: 2026-06-09
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def strip_tags(text):
    return re.sub(r'<[^>]+>', '', text or "").strip()


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.read()
    except Exception:
        return None


def parse_items(raw):
    items = []
    try:
        root = ET.fromstring(raw)
    except Exception:
        return items

    atom_ns = "http://www.w3.org/2005/Atom"
    dc_ns   = "http://purl.org/dc/elements/1.1/"

    # RSS 2.0
    for item in root.iter("item"):
        def t(tag):
            el = item.find(tag)
            return (el.text or "").strip() if el is not None else ""
        items.append({
            "title":   html_mod.unescape(t("title")),
            "link":    t("link"),
            "date":    parse_date(t("pubDate")),
            "summary": strip_tags(t("description"))[:250],
        })

    # Atom
    for entry in root.iter(f"{{{atom_ns}}}entry"):
        def ta(tag):
            el = entry.find(f"{{{atom_ns}}}{tag}")
            return (el.text or "").strip() if el is not None else ""
        link_el = entry.find(f"{{{atom_ns}}}link")
        link = link_el.get("href", "") if link_el is not None else ""
        summary = strip_tags(ta("summary") or ta("content"))[:250]
        items.append({
            "title":   html_mod.unescape(ta("title")),
            "link":    link,
            "date":    parse_date(ta("published") or ta("updated")),
            "summary": summary,
        })

    return items


def is_ai_related(item):
    text = (item["title"] + " " + item["summary"]).lower()
    return any(kw in text for kw in AI_KEYWORDS)


def main():
    yesterday = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)
    results = {}  # outlet -> list of articles
    seen_urls = set()

    for outlet, config in OUTLETS.items():
        for feed_url in config["feeds"]:
            raw = fetch(feed_url)
            if not raw:
                continue
            for item in parse_items(raw):
                link = item["link"]
                if not link or link in seen_urls:
                    continue
                # Accept if date matches yesterday, or if date is missing (include anyway)
                if item["date"] and item["date"] != yesterday:
                    continue
                if not is_ai_related(item):
                    continue
                seen_urls.add(link)
                results.setdefault(outlet, []).append(item)

    date_str = yesterday.strftime("%B %d, %Y")
    lines = [f"# AI News Digest — {date_str}\n"]

    total = sum(len(v) for v in results.values())

    if not results:
        lines.append("_No AI articles found yesterday across tracked outlets._\n")
    else:
        lines.append(f"**{total} article(s)** across {len(results)} outlet(s).\n")
        for outlet, config in OUTLETS.items():
            articles = results.get(outlet)
            if not articles:
                continue
            journalists = " · ".join(config["journalists"])
            lines.append(f"\n## {outlet}")
            lines.append(f"_Tracked journalists: {journalists}_\n")
            for a in articles:
                lines.append(f"### [{a['title']}]({a['link']})")
                if a["summary"]:
                    lines.append(f"> {a['summary']}...\n")
                lines.append("")

    lines.append("---")
    lines.append("_Automated AI news digest · tracked outlets: The Guardian · NYT · WIRED · Bloomberg · The Atlantic · POLITICO · TIME · Washington Post · BBC · AP · The Economist · Financial Times_")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
