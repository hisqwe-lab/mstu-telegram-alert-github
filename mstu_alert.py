import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
SETTINGS_PATH = BASE_DIR / "settings.txt"
STATE_PATH = BASE_DIR / "state.json"

USER_AGENT = (
    "mstu-telegram-alert/1.0 "
    "(personal MSTU split monitor; contact: local-user)"
)

KEYWORDS = [
    "reverse split",
    "stock split",
    "share split",
    "split",
    "share consolidation",
    "consolidation",
    "ratio",
    "effective date",
    "payable date",
    "distribution date",
    "cusip",
]

MSTU_TERMS = [
    "mstu",
    "t-rex 2x long mstr",
    "2x long mstr",
    "mstr daily target",
    "26923n173",
]

SOURCES = [
    {
        "name": "REX Shares MSTU official page",
        "url": "https://www.rexshares.com/mstu/",
        "kind": "html",
    },
    {
        "name": "REX Shares News & Insights",
        "url": "https://www.rexshares.com/news-insights/",
        "kind": "html",
    },
    {
        "name": "SEC EDGAR MSTU feed",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?CIK=MSTU&owner=exclude&action=getcompany&count=100&output=atom",
        "kind": "atom",
    },
    {
        "name": "Google News MSTU split search",
        "url": "https://news.google.com/rss/search?q="
        + urllib.parse.quote('"MSTU" ("reverse split" OR "stock split" OR split OR consolidation)')
        + "&hl=en-US&gl=US&ceid=US:en",
        "kind": "rss",
    },
]


def load_env():
    values = {}
    for config_path in [ENV_PATH, SETTINGS_PATH]:
        if not config_path.exists():
            continue
        for raw_line in config_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed_key = key.strip()
            parsed_value = value.strip().strip('"').strip("'")
            if parsed_value in {"put_your_bot_token_here", "put_your_chat_id_here"}:
                continue
            values[parsed_key] = parsed_value
    values.update({k: v for k, v in os.environ.items() if k.startswith("TELEGRAM_")})
    if "ALERT_ON_FIRST_RUN" in os.environ:
        values["ALERT_ON_FIRST_RUN"] = os.environ["ALERT_ON_FIRST_RUN"]
    return values


def load_state():
    if not STATE_PATH.exists():
        return {"seen": [], "created_at": int(time.time())}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = STATE_PATH.with_suffix(".broken.json")
        STATE_PATH.replace(backup)
        return {"seen": [], "created_at": int(time.time())}


def save_state(state):
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/rss+xml,application/atom+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def clean_text(text):
    text = html.unescape(text)
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_feed_items(source, content):
    items = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return items

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "rss_content": "http://purl.org/rss/1.0/modules/content/",
    }

    for entry in root.findall(".//atom:entry", ns):
        title = entry.findtext("atom:title", default="", namespaces=ns)
        summary = entry.findtext("atom:summary", default="", namespaces=ns)
        updated = entry.findtext("atom:updated", default="", namespaces=ns)
        link_node = entry.find("atom:link", ns)
        link = link_node.attrib.get("href", source["url"]) if link_node is not None else source["url"]
        items.append(
            {
                "source": source["name"],
                "title": clean_text(title),
                "text": clean_text(f"{title} {summary} {updated}"),
                "url": link,
            }
        )

    for item in root.findall(".//channel/item"):
        title = item.findtext("title", default="")
        description = item.findtext("description", default="")
        pub_date = item.findtext("pubDate", default="")
        link = item.findtext("link", default=source["url"])
        items.append(
            {
                "source": source["name"],
                "title": clean_text(title),
                "text": clean_text(f"{title} {description} {pub_date}"),
                "url": link,
            }
        )

    return items


def parse_html_item(source, content):
    text = clean_text(content)
    return [
        {
            "source": source["name"],
            "title": source["name"],
            "text": text[:12000],
            "url": source["url"],
        }
    ]


def has_match(item):
    lowered = item["text"].lower()
    return any(term in lowered for term in MSTU_TERMS) and any(
        keyword in lowered for keyword in KEYWORDS
    )


def fingerprint(item):
    relevant = f'{item["source"]}|{item["title"]}|{item["url"]}|{item["text"][:2000]}'
    return hashlib.sha256(relevant.encode("utf-8")).hexdigest()


def matched_keywords(item):
    lowered = item["text"].lower()
    return [kw for kw in KEYWORDS if kw in lowered]


def excerpt(item):
    text = item["text"]
    lowered = text.lower()
    positions = [lowered.find(kw) for kw in KEYWORDS if lowered.find(kw) >= 0]
    if not positions:
        return text[:400]
    start = max(min(positions) - 160, 0)
    end = min(start + 520, len(text))
    return text[start:end].strip()


def send_telegram(config, message):
    token = config.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = config.get("TELEGRAM_CHAT_ID", "")
    if (
        not token
        or not chat_id
        or token == "put_your_bot_token_here"
        or chat_id == "put_your_chat_id_here"
    ):
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": "false",
        }
    ).encode("utf-8")
    req = urllib.request.Request(api_url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram API error {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Telegram API: {exc}") from exc


def build_alert(item):
    kws = ", ".join(matched_keywords(item))
    return (
        "[MSTU Alert]\n"
        "분할/병합 관련 키워드가 감지됐습니다.\n\n"
        f"Source: {item['source']}\n"
        f"Title: {item['title'] or '(no title)'}\n"
        f"Keywords: {kws}\n"
        f"URL: {item['url']}\n\n"
        f"Excerpt:\n{excerpt(item)}"
    )


def build_heartbeat():
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S KST")
    source_lines = "\n".join(f"- {source['name']}" for source in SOURCES)
    return (
        "[MSTU Alert] 감시 상태 확인\n\n"
        "MSTU 분할/병합 감시가 실행 중입니다.\n"
        f"Time: {now_kst}\n\n"
        "Monitoring:\n"
        f"{source_lines}\n\n"
        "새 MSTU 분할/병합 관련 소식이 발견되면 별도 알림을 보냅니다."
    )


def collect_matches():
    matches = []
    errors = []
    for source in SOURCES:
        try:
            content = fetch(source["url"])
            if source["kind"] in {"atom", "rss"}:
                items = parse_feed_items(source, content)
            else:
                items = parse_html_item(source, content)
            matches.extend([item for item in items if has_match(item)])
        except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
            errors.append(f"{source['name']}: {exc}")
    return matches, errors


def show_sources():
    print("Monitoring sources:")
    for index, source in enumerate(SOURCES, start=1):
        print(f"{index}. {source['name']}")
        print(f"   {source['url']}")
    print()
    print("MSTU terms:")
    for term in MSTU_TERMS:
        print(f"- {term}")
    print()
    print("Split/reverse split keywords:")
    for keyword in KEYWORDS:
        print(f"- {keyword}")


def preview_sources():
    print("Checking monitored sources without sending Telegram alerts...\n")
    total_matches = 0
    for source in SOURCES:
        print(f"[{source['name']}]")
        print(source["url"])
        try:
            content = fetch(source["url"])
            if source["kind"] in {"atom", "rss"}:
                items = parse_feed_items(source, content)
            else:
                items = parse_html_item(source, content)
            matches = [item for item in items if has_match(item)]
            total_matches += len(matches)
            print(f"Fetched items: {len(items)}")
            print(f"Matched items: {len(matches)}")
            for item in matches[:5]:
                kws = ", ".join(matched_keywords(item))
                print(f"- {item['title'] or '(no title)'}")
                print(f"  Keywords: {kws}")
                print(f"  URL: {item['url']}")
                print(f"  Excerpt: {excerpt(item)[:240]}")
            if len(matches) > 5:
                print(f"  ...and {len(matches) - 5} more")
        except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
            print(f"Error: {exc}")
        print()
    print(f"Total matched items: {total_matches}")


def check_once(config):
    state = load_state()
    seen = set(state.get("seen", []))
    first_run = not seen
    alert_on_first_run = config.get("ALERT_ON_FIRST_RUN", "0") == "1"

    matches, errors = collect_matches()
    new_items = []

    for item in matches:
        item_id = fingerprint(item)
        if item_id not in seen:
            seen.add(item_id)
            item["id"] = item_id
            new_items.append(item)

    state["seen"] = sorted(seen)
    state["last_checked_at"] = int(time.time())
    state["last_error"] = errors[-5:]
    save_state(state)

    should_alert = new_items and (alert_on_first_run or not first_run)
    if should_alert:
        for item in new_items:
            send_telegram(config, build_alert(item))
            time.sleep(1)

    print(
        json.dumps(
            {
                "matches": len(matches),
                "new": len(new_items),
                "alerted": len(new_items) if should_alert else 0,
                "first_run": first_run,
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description="MSTU split/reverse split Telegram monitor")
    parser.add_argument("--test-telegram", action="store_true", help="send a test Telegram message")
    parser.add_argument("--check-once", action="store_true", help="check sources once")
    parser.add_argument("--heartbeat", action="store_true", help="send a monitoring status Telegram message")
    parser.add_argument("--show-sources", action="store_true", help="show monitored sources and keywords")
    parser.add_argument("--preview", action="store_true", help="check sources and print matches without Telegram alerts")
    args = parser.parse_args()

    config = load_env()

    if args.show_sources:
        show_sources()
        return

    if args.preview:
        preview_sources()
        return

    if args.test_telegram:
        send_telegram(
            config,
            "[MSTU Alert] 테스트 메시지입니다. 이 메시지가 보이면 텔레그램 설정이 정상입니다.",
        )
        print("Test message sent.")
        return

    if args.heartbeat:
        send_telegram(config, build_heartbeat())
        print("Heartbeat message sent.")
        return

    if args.check_once:
        check_once(config)
        return

    parser.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
