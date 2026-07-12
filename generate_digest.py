#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
毎日のニュースダイジェスト生成スクリプト（無料版）
Google News の RSS フィード（無料・APIキー不要）から、4分野それぞれ
最新ニュースを取得し、1枚のHTMLページ (docs/index.html) を生成する。
"""

import html
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

ITEMS_PER_TOPIC = 5

TOPICS = [
    {
        "key": "education",
        "title": "日本の教育（高等学校）",
        "query": '(高校教育 OR 高等学校 OR 学習指導要領 OR 文部科学省) 教育 when:7d',
    },
    {
        "key": "archaeology",
        "title": "史学・考古学（日本）",
        "query": '(考古学 OR 遺跡 OR 発掘調査 OR 出土) 日本 when:7d',
    },
    {
        "key": "history_education",
        "title": "日本史教育（高等学校）",
        "query": '(日本史 OR 歴史総合 OR 歴史教育) 高校 when:7d',
    },
    {
        "key": "exam",
        "title": "大学受験（日本）",
        "query": '(大学受験 OR 大学入試 OR 共通テスト) when:7d',
    },
]

JST = timezone(timedelta(hours=9))
USER_AGENT = "Mozilla/5.0 (compatible; DailyDigestBot/1.0)"


def fetch_topic_items(topic: dict) -> list:
    query = urllib.parse.quote(topic["query"])
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except Exception as e:
        print(f"[ERROR] {topic['title']}: RSS取得失敗 {e}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"[ERROR] {topic['title']}: XML解析失敗 {e}", file=sys.stderr)
        return []

    items = []
    seen_titles = set()
    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title", default=""))
        link = item.findtext("link", default="")
        pub_date = item.findtext("pubDate", default="")
        source_el = item.find("source")
        source = clean_text(source_el.text) if source_el is not None and source_el.text else ""

        if not title or not link:
            continue
        if title in seen_titles:
            continue
        seen_titles.add(title)

        items.append({
            "title": title,
            "link": link,
            "source": source,
            "date": format_pub_date(pub_date),
        })

        if len(items) >= ITEMS_PER_TOPIC:
            break

    return items


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()


def format_pub_date(pub_date: str) -> str:
    if not pub_date:
        return ""
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
        dt = dt.replace(tzinfo=timezone.utc).astimezone(JST)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return pub_date


def build_html(results: dict, generated_at: datetime) -> str:
    date_str = generated_at.strftime("%Y年%m月%d日 (%a)")

    sections_html = []
    for topic in TOPICS:
        items = results.get(topic["key"], [])
        if items:
            cards = "\n".join(build_card(item) for item in items)
        else:
            cards = '<p class="empty">本日は取得できませんでした。</p>'
        sections_html.append(f"""
        <section class="topic">
          <h2>{escape(topic['title'])}</h2>
          <div class="cards">
            {cards}
          </div>
        </section>""")

    return HTML_TEMPLATE.format(
        date_str=escape(date_str),
        sections="\n".join(sections_html),
    )


def build_card(item: dict) -> str:
    title = escape(item.get("title", "(タイトル不明)"))
    source = escape(item.get("source", ""))
    date = escape(item.get("date", ""))
    url = item.get("link", "#")
    meta = " ・ ".join(x for x in [source, date] if x)
    return f"""
    <a class="card" href="{escape(url)}" target="_blank" rel="noopener">
      <div class="card-title">{title}</div>
      <div class="card-meta">{meta}</div>
    </a>"""


def escape(s: str) -> str:
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>日次ニュースダイジェスト</title>
<style>
  :root {{
    --bg: #f7f5f2;
    --card-bg: #ffffff;
    --ink: #2b2b2b;
    --sub: #6b6b6b;
    --accent: #8a3b2f;
    --border: #e5e0d8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic", sans-serif;
    background: var(--bg);
    color: var(--ink);
    line-height: 1.6;
  }}
  header {{
    padding: 28px 20px 16px;
    max-width: 880px;
    margin: 0 auto;
  }}
  header h1 {{
    margin: 0 0 4px;
    font-size: 1.5rem;
  }}
  header .date {{
    color: var(--sub);
    font-size: 0.95rem;
  }}
  main {{
    max-width: 880px;
    margin: 0 auto;
    padding: 0 20px 60px;
  }}
  .topic {{
    margin-top: 32px;
  }}
  .topic h2 {{
    font-size: 1.15rem;
    border-left: 5px solid var(--accent);
    padding-left: 10px;
    margin-bottom: 14px;
  }}
  .cards {{
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}
  .card {{
    display: block;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
    text-decoration: none;
    color: inherit;
  }}
  .card:hover {{
    border-color: var(--accent);
  }}
  .card-title {{
    font-weight: 600;
    font-size: 1rem;
    margin-bottom: 4px;
  }}
  .card-meta {{
    font-size: 0.8rem;
    color: var(--sub);
  }}
  .empty {{
    color: var(--sub);
    font-size: 0.9rem;
  }}
  footer {{
    text-align: center;
    color: var(--sub);
    font-size: 0.8rem;
    padding: 20px;
  }}
</style>
</head>
<body>
<header>
  <h1>日次ニュースダイジェスト</h1>
  <div class="date">{date_str} 更新</div>
</header>
<main>
{sections}
</main>
<footer>Google News RSS + GitHub Actions により毎朝自動生成（無料）</footer>
</body>
</html>
"""


def main():
    results = {}
    for topic in TOPICS:
        print(f"取得中: {topic['title']}")
        items = fetch_topic_items(topic)
        results[topic["key"]] = items
        print(f"  -> {len(items)}件取得")

    generated_at = datetime.now(JST)
    html_out = build_html(results, generated_at)

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"生成完了: {out_path}")


if __name__ == "__main__":
    main()
