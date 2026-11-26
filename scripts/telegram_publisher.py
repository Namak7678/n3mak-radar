#!/usr/bin/env python3
"""
N3mak Radar — Trilingual Publisher (Telegram + Discord, AR / EN / RU)
Reads the latest exposure-index dataset and posts a daily brief to:
  - Telegram channels (bot must be admin with 'post messages' permission)
  - Discord channels (via incoming webhook URLs)

Language routing (env vars / repo secrets):
  Telegram: N3MAK_CHAT_AR / N3MAK_CHAT_EN / N3MAK_CHAT_RU
  Discord:  N3MAK_DISCORD_WEBHOOK_AR / N3MAK_DISCORD_WEBHOOK_EN / N3MAK_DISCORD_WEBHOOK_RU
Only targets with a configured value are posted.

Data source: n3mak-exposure-index/data/latest.json (same owner, public repo).
This script only republishes metadata already published by leak groups.
"""

import json
import os
import sys
import urllib.request
import urllib.error

DATA_URL = os.environ.get(
    "N3MAK_DATA_URL",
    "https://raw.githubusercontent.com/Namak7678/n3mak-exposure-index/main/data/latest.json",
)
BOT_TOKEN = os.environ.get("N3MAK_BOT_TOKEN", "")
CHAT_AR = os.environ.get("N3MAK_CHAT_AR", "")
CHAT_EN = os.environ.get("N3MAK_CHAT_EN", "")
CHAT_RU = os.environ.get("N3MAK_CHAT_RU", "")
DISCORD_AR = os.environ.get("N3MAK_DISCORD_WEBHOOK_AR", "")
DISCORD_EN = os.environ.get("N3MAK_DISCORD_WEBHOOK_EN", "")
DISCORD_RU = os.environ.get("N3MAK_DISCORD_WEBHOOK_RU", "")

RADAR_URL = "https://namak7678.github.io/n3mak-radar/"
BOT_URL = "https://t.me/N3mak_bot"


def http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "n3mak-publisher/1.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_to_telegram(chat_id: str, text: str) -> None:
    url = "https://api.telegram.org/bot%s/sendMessage" % BOT_TOKEN
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        if not result.get("ok"):
            raise RuntimeError("Telegram API rejected the message: %s" % result)


def html_to_markdown(text: str) -> str:
    """Convert the Telegram HTML brief to Discord-friendly markdown."""
    text = text.replace("<b>", "**").replace("</b>", "**")
    text = text.replace("<i>", "_").replace("</i>", "_")
    return text


def post_to_discord(webhook_url: str, text: str) -> None:
    content = html_to_markdown(text)
    if len(content) > 1900:  # Discord hard limit is 2000
        content = content[:1900]
    payload = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 204):
            raise RuntimeError("Discord webhook rejected the message: HTTP %s" % resp.status)


def top_countries(data: dict, limit: int = 5) -> list:
    countries = sorted(data.get("countries", []), key=lambda c: c.get("victims", 0), reverse=True)
    return countries[:limit]


def total_victims(data: dict) -> int:
    return sum(c.get("victims", 0) for c in data.get("countries", []))


def fmt_updated(iso: str) -> str:
    # 2026-11-26T13:46:36.824Z -> 2026-11-26 13:46 UTC
    return iso[:16].replace("T", " ") + " UTC"


def build_brief_ar(data: dict) -> str:
    top = top_countries(data)
    top_line = " \u00b7 ".join("%s (%d)" % (c["country"], c["victims"]) for c in top)
    return (
        "\U0001F4E1 <b>\u0646\u0639\u0645\u0643 | \u0645\u0648\u062C\u0632 \u0627\u0644\u0631\u0627\u062F\u0627\u0631 \u2014 %s</b>\n\n"
        "\u0625\u062C\u0645\u0627\u0644\u064A \u0627\u0644\u0625\u0634\u0627\u0631\u0627\u062A \u0627\u0644\u0645\u0646\u0634\u0648\u0631\u0629: <b>%d</b>\n"
        "\U0001F534 \u0623\u0639\u0644\u0649 \u0627\u0644\u062F\u0648\u0644: %s\n\n"
        "<i>\u0625\u0634\u0627\u0631\u0627\u062A \u0645\u062C\u0645\u0651\u0639\u0629 \u0645\u0646 \u0645\u0648\u0627\u0642\u0639 \u0627\u0644\u0646\u0634\u0631 \u0627\u0644\u0639\u0644\u0646\u064A\u0629 \u0644\u0644\u0645\u062C\u0645\u0648\u0639\u0627\u062A \u2014 \u0627\u062F\u0639\u0627\u0621\u0627\u062A \u063A\u064A\u0631 \u0645\u0624\u0643\u062F\u0629</i>\n"
        "\U0001F4C0 \u0627\u0644\u0644\u0648\u062D\u0629 \u0627\u0644\u0643\u0627\u0645\u0644\u0629 \u2192 %s\n"
        "\U0001F916 \u062A\u0646\u0628\u064A\u0647\u0627\u062A \u0641\u0648\u0631\u064A\u0629 \u0648\u062A\u0642\u0627\u0631\u064A\u0631 \u0645\u062A\u0646\u0648\u0639\u0629 \u2192 %s"
    ) % (fmt_updated(data.get("updated", "")), total_victims(data), top_line, RADAR_URL, BOT_URL)


def build_brief_en(data: dict) -> str:
    top = top_countries(data)
    top_line = " \u00b7 ".join("%s (%d)" % (c["country"], c["victims"]) for c in top)
    return (
        "\U0001F4E1 <b>N3mak Radar | Daily Brief \u2014 %s</b>\n\n"
        "Total published signals: <b>%d</b>\n"
        "\U0001F534 Top countries: %s\n\n"
        "<i>Signals aggregated from public leak-site listings \u2014 unverified operator claims</i>\n"
        "\U0001F4C0 Full board: %s\n"
        "\U0001F916 Instant alerts & reports: %s"
    ) % (fmt_updated(data.get("updated", "")), total_victims(data), top_line, RADAR_URL, BOT_URL)


def build_brief_ru(data: dict) -> str:
    top = top_countries(data)
    top_line = " \u00b7 ".join("%s (%d)" % (c["country"], c["victims"]) for c in top)
    return (
        "\U0001F4E1 <b>N3mak Radar | \u0415\u0436\u0435\u0434\u043D\u0435\u0432\u043D\u0430\u044F \u0441\u0432\u043E\u0434\u043A\u0430 \u2014 %s</b>\n\n"
        "\u0412\u0441\u0435\u0433\u043E \u043E\u043F\u0443\u0431\u043B\u0438\u043A\u043E\u0432\u0430\u043D\u043D\u044B\u0445 \u0441\u0438\u0433\u043D\u0430\u043B\u043E\u0432: <b>%d</b>\n"
        "\U0001F534 \u041B\u0438\u0434\u0435\u0440\u044B \u043F\u043E \u0441\u0442\u0440\u0430\u043D\u0430\u043C: %s\n\n"
        "<i>\u0421\u0438\u0433\u043D\u0430\u043B\u044B \u0441\u043E\u0431\u0440\u0430\u043D\u044B \u0438\u0437 \u043F\u0443\u0431\u043B\u0438\u0447\u043D\u044B\u0445 \u043B\u0438\u0441\u0442\u0438\u043D\u0433\u043E\u0432 leak-\u0441\u0430\u0439\u0442\u043E\u0432 \u2014 \u0437\u0430\u044F\u0432\u043B\u0435\u043D\u0438\u044F \u0433\u0440\u0443\u043F\u043F \u0431\u0435\u0437 \u043F\u043E\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043D\u0438\u044F</i>\n"
        "\U0001F4C0 \u041F\u043E\u043B\u043D\u0430\u044F \u0434\u043E\u0441\u043A\u0430: %s\n"
        "\U0001F916 \u041C\u0433\u043D\u043E\u0432\u0435\u043D\u043D\u044B\u0435 \u0443\u0432\u0435\u0434\u043E\u043C\u043B\u0435\u043D\u0438\u044F \u0438 \u043E\u0442\u0447\u0451\u0442\u044B: %s"
    ) % (fmt_updated(data.get("updated", "")), total_victims(data), top_line, RADAR_URL, BOT_URL)


def main() -> int:
    data = http_json(DATA_URL)

    briefs = {
        "AR": build_brief_ar(data),
        "EN": build_brief_en(data),
        "RU": build_brief_ru(data),
    }

    targets = []
    if BOT_TOKEN:
        targets += [
            ("telegram", CHAT_AR, "AR"), ("telegram", CHAT_EN, "EN"), ("telegram", CHAT_RU, "RU"),
        ]
    else:
        print("NOTE: N3MAK_BOT_TOKEN not set; Telegram targets skipped.")
    targets += [
        ("discord", DISCORD_AR, "AR"), ("discord", DISCORD_EN, "EN"), ("discord", DISCORD_RU, "RU"),
    ]

    posted, failures = 0, []
    for kind, target, lang in targets:
        if not target:
            print("SKIP %s/%s: not configured." % (kind, lang))
            continue
        try:
            if kind == "telegram":
                post_to_telegram(target, briefs[lang])
            else:
                post_to_discord(target, briefs[lang])
            posted += 1
            print("POSTED %s -> %s" % (lang, kind))
        except Exception as exc:  # noqa: BLE001
            failures.append(("%s/%s" % (kind, lang), str(exc)))
            print("FAILED %s/%s: %s" % (kind, lang, exc), file=sys.stderr)

    if posted == 0 and not failures:
        print("No targets configured; nothing posted.")
        return 0
    if failures:
        print("Failures: %s" % failures, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
