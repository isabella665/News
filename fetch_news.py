#!/usr/bin/env python3
"""Fetch yesterday's AI articles from tracked journalists. Uses stdlib only."""

import sys
import datetime
import urllib.request
import xml.etree.ElementTree as ET
import re
import html

JOURNALISTS = {
    "Dan Milmo":        "The Guardian",
    "Karen Hao":        "The Atlantic",
    "Kevin Roose":      "The New York Times",
    "Rachel Metz":      "Bloomberg",
    "Cade Metz":        "The New York Times",
    "Ezra Klein":       "NYT / podcast",
    "Steven Levy":      "WIRED",
    "Alex Hern":        "The Guardian",
    "Dina Bass":        "Bloomberg",
    "Kenneth Cukier":   "The Economist",
    "Will Knight":      "WIRED",
    "Madhumita Murgia": "Financial Times",
    "Melissa Heikkilä": "POLITICO",
    "Billy Perrigo":    "TIME",
    "Gerrit De Vynck":  "Washington Post",
    "Marc Cieslak":     "BBC",
    "Kelvin Chan":      "AP",
    "Matteo Wong":      "The Atlantic",
}

FEEDS = [
    "https://www.theguardian.com/technology/artificialintelligenceai/rss",
    "https://www.theguardian.com/technology/rss",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
    "https://www.wired.com/feed/category/artificial-intelligence/latest/rss",
    "https://www.wired.com/feed/rss",
    "https://www.theatlantic.com/feed/all/",
    "https://feeds.bloomberg.com/technology/news.rss",
    "https://rss.politico.com/politics-news.xml",
    "https://time.com/feed/",
    "https://feeds.washingtonpost.com/rss/business/technology",
    "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.apnews.com/rss/apf-technology",
    "https://www.economist.com/science-and-technology/rss.xml",
    "https://www.ft.com/rss/home/technology",
]

AI_KEYWORDS = [
    "artificial intelligence", " ai ", "machine learning", "large language model",
    "llm", "openai", "anthropic", "deepmind", "chatgpt", "gpt", "gemini",
    "claude", "neural network", "generative ai", "ai safety", "ai regulation",
    "ai governance",
]

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_rfc822(s):
    """Parse RFC 822 date string to date, return None on failure."""
    if not s:
        return None
    try:
        # e.g. "Mon, 09 Jun 2026 08:00:00 +0000"
        parts = s.strip().split()
        # find day, month, year
        for i, p in enumerate(parts):
            if p[:3].lower() in MONTHS and i >= 1:
                day = int(parts[i - 1].rstrip(","))
                month = MONTHS[p[:3].lower()]
                year = int(parts[i + 1])
                return datetime.date(year, month, day)
    except Exception:
        pass
    # Try ISO-ish: 2026-06-09
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def strip_tags(text):
    return re.sub(r'<[^>]+>', '', text or "")


def fetch_feed(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.read()
    except Exception:
        return None


def parse_feed(raw):
    """Return list of dicts with title, link, author, date_str, summary."""
    items = []
    try:
        root = ET.fromstring(raw)
    except Exception:
        return items

    ns = {
        "dc":      "http://purl.org/dc/elements/1.1/",
        "media":   "http://search.yahoo.com/mrss/",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "atom":    "http://www.w3.org/2005/Atom",
    }

    # RSS 2.0
    for item in root.iter("item"):
        def t(tag, default=""):
            el = item.find(tag)
            return (el.text or "") if el is not None else default

        def tns(prefix, tag, default=""):
            el = item.find(f"{{{ns[prefix]}}}{tag}")
            return (el.text or "") if el is not None else default

        author = t("author") or tns("dc", "creator")
        summary = strip_tags(t("description"))[:300]
        items.append({
            "title":    html.unescape(t("title")),
            "link":     t("link"),
            "author":   author,
            "date_str": t("pubDate"),
            "summary":  summary,
        })

    # Atom
    atom_ns = "http://www.w3.org/2005/Atom"
    for entry in root.iter(f"{{{atom_ns}}}entry"):
        def ta(tag, default=""):
            el = entry.find(f"{{{atom_ns}}}{tag}")
            return (el.text or "") if el is not None else default

        author_el = entry.find(f"{{{atom_ns}}}author/{{{atom_ns}}}name")
        author = author_el.text if author_el is not None else ""
        link_el = entry.find(f"{{{atom_ns}}}link")
        link = link_el.get("href", "") if link_el is not None else ""
        summary = strip_tags(ta("summary") or ta("content"))[:300]
        items.append({
            "title":    html.unescape(ta("title")),
            "link":     link,
            "author":   author,
            "date_str": ta("published") or ta("updated"),
            "summary":  summary,
        })

    return items


def is_ai_related(item):
    text = (item["title"] + " " + item["summary"]).lower()
    return any(kw in text for kw in AI_KEYWORDS)


def main():
    yesterday = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)
    found = []
    seen_urls = set()

    for feed_url in FEEDS:
        raw = fetch_feed(feed_url)
        if not raw:
            continue
        for item in parse_feed(raw):
            link = item["link"]
            if not link or link in seen_urls:
                continue

            pub_date = parse_rfc822(item["date_str"])
            if pub_date and pub_date != yesterday:
                continue

            author_raw = item["author"].lower()
            matched = None
            for journalist in JOURNALISTS:
                if journalist.lower() in author_raw:
                    matched = journalist
                    break
            if not matched:
                continue

            if not is_ai_related(item):
                continue

            seen_urls.add(link)
            found.append({
                "journalist": matched,
                "outlet":     JOURNALISTS[matched],
                "title":      item["title"],
                "link":       link,
                "summary":    item["summary"],
            })

    by_journalist = {}
    for item in found:
        by_journalist.setdefault(item["journalist"], []).append(item)

    date_str = yesterday.strftime("%B %d, %Y")
    lines = [f"# AI News Digest — {date_str}\n"]

    if not found:
        lines.append("_No articles found from tracked journalists yesterday._\n")
        lines.append("This may mean a slow news day or some feeds were unavailable.\n")
    else:
        lines.append(f"**{len(found)} article(s)** from {len(by_journalist)} journalist(s).\n")
        for journalist, articles in sorted(by_journalist.items()):
            outlet = JOURNALISTS[journalist]
            lines.append(f"\n## {journalist} — {outlet}\n")
            for a in articles:
                lines.append(f"### [{a['title']}]({a['link']})")
                if a["summary"]:
                    lines.append(f"> {a['summary'].strip()}...\n")
                lines.append("")

    lines.append("---")
    lines.append("_Tracked outlets: The Guardian · NYT · WIRED · Bloomberg · The Atlantic · POLITICO · TIME · Washington Post · BBC · AP · The Economist · Financial Times_")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
