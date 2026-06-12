#!/usr/bin/env python3
"""Подтягивает новые выпуски правового мониторинга из публичной веб-версии
телеграм-канала t.me/s/pmgchp в src/data/monitoring.json.

Запускается в GitHub Actions по расписанию. Добавляет только новые сообщения
(id больше максимального в json), начинающиеся с «Правовой мониторинг за…».
Пункты оглавления берутся из текста сообщения, если они там есть.
"""
import json
import re
import html
import urllib.request
import pathlib
import sys

DATA = pathlib.Path(__file__).parent.parent / "src/data/monitoring.json"
CHANNEL = "pmgchp"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def parse_page(page):
    """-> list of (id, iso_dt, text)"""
    out = []
    for block in page.split("tgme_widget_message_wrap")[1:]:
        mid = re.search(r'data-post="%s/(\d+)"' % CHANNEL, block)
        dt = re.search(r'<time datetime="([^"]+)"', block)
        if not (mid and dt):
            continue
        m = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>\s*<', block, re.S)
        text = ""
        if m:
            t = re.sub(r"<br/?>", "\n", m.group(1))
            text = html.unescape(re.sub(r"<[^>]+>", "", t))
        out.append((int(mid.group(1)), dt.group(1), text))
    return out


def main():
    releases = json.load(open(DATA))
    known = {r["id"] for r in releases}
    max_id = max(known)

    msgs = parse_page(fetch(f"https://t.me/s/{CHANNEL}"))
    if not msgs:
        print("ОШИБКА: не распарсено ни одного сообщения — вероятно, изменился HTML t.me/s")
        return 1
    skipped_old = skipped_non_monitoring = 0
    new = []
    for mid, dt, text in msgs:
        if mid <= max_id or mid in known:
            skipped_old += 1
            continue
        first = text.split("\n", 1)[0].strip()
        if not re.match(r"(?i)правовой мониторинг за", first):
            skipped_non_monitoring += 1
            continue
        period = re.sub(r"(?i)^правовой мониторинг за\s*", "", re.sub(r"\s+", " ", first)).rstrip(".").strip()
        items = []
        seen = set()
        for ln in text.split("\n")[1:]:
            ln = ln.strip()
            if not ln or re.match(r"(?i)(подготовлено с использованием|#|ссылки на документы|в нем ключевые)", ln):
                continue
            mm = re.match(r"^(?:\d+[.)]\s*|[-•▪️]\s*)(.+)$", ln)
            if mm:
                item = re.sub(r"\s+", " ", mm.group(1)).strip()
                key = item.lower()
                if key not in seen:  # дедупликация с сохранением порядка
                    seen.add(key)
                    items.append(item)
        new.append({"id": mid, "date": dt[:10], "period": period, "items": items})

    print(f"сообщений распарсено: {len(msgs)} | известный max_id: {max_id} | "
          f"пропущено старых: {skipped_old} | пропущено не-мониторинга: {skipped_non_monitoring} | "
          f"новых выпусков: {len(new)}")
    if not new:
        print("новых выпусков нет")
        return 0

    releases = sorted(releases + new, key=lambda r: r["id"], reverse=True)
    json.dump(releases, open(DATA, "w"), ensure_ascii=False, indent=1)
    print(f"добавлено выпусков: {len(new)}: " + ", ".join(r["period"] for r in new))
    return 0


FIXTURE = """
<div class="tgme_widget_message_wrap js-widget_message_wrap">
 <div class="tgme_widget_message" data-post="pmgchp/999">
  <div class="tgme_widget_message_text js-message_text" dir="auto">Правовой мониторинг за 1 - 6 июня 2099 г.<br/><br/>1. Первый пункт обзора<br/>2. Второй пункт обзора<br/>2. Второй пункт обзора<br/>Подготовлено с использованием СПС «Консультант Плюс»<br/>#правовоймониторинг</div>
  <time datetime="2099-06-08T05:00:00+00:00"></time>
 </div>
</div>
"""


def selftest():
    """Fixture-тест парсера: формат t.me/s и дедупликация items."""
    msgs = parse_page(FIXTURE)
    assert len(msgs) == 1, f"ожидалось 1 сообщение, получено {len(msgs)}"
    mid, dt, text = msgs[0]
    assert mid == 999 and dt.startswith("2099-06-08"), (mid, dt)
    first = text.split("\n", 1)[0].strip()
    assert re.match(r"(?i)правовой мониторинг за", first), f"заголовок не распознан: {first!r}"
    items, seen = [], set()
    for ln in text.split("\n")[1:]:
        mm = re.match(r"^(?:\d+[.)]\s*|[-•▪️]\s*)(.+)$", ln.strip())
        if mm:
            item = re.sub(r"\s+", " ", mm.group(1)).strip()
            if item.lower() not in seen:
                seen.add(item.lower())
                items.append(item)
    assert items == ["Первый пункт обзора", "Второй пункт обзора"], items
    print("selftest OK: парсинг сообщения и дедупликация работают")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
