#!/usr/bin/env python3
"""Smoke-проверка собранного сайта в dist/: ключевые файлы и внутренние ссылки.

Запуск после `npm run build`: python3 scripts/check_dist.py
Падает (код 1), если отсутствует ключевой файл или внутренняя ссылка ведёт в никуда.
"""
import re
import sys
import pathlib
from urllib.parse import unquote

DIST = pathlib.Path(__file__).parent.parent / "dist"

REQUIRED = [
    "index.html",
    "monitoring/index.html",
    "blog/index.html",
    "experience/index.html",
    "search/index.html",
    "terms/index.html",
    "404.html",
    "rss.xml",
    "robots.txt",
    "sitemap-index.xml",
    "pagefind/pagefind-ui.js",
    "pagefind/pagefind-ui.css",
    ".nojekyll",
]


def target_exists(href):
    path = unquote(href.split("#")[0].split("?")[0]).lstrip("/")
    if not path:
        return True
    p = DIST / path
    return p.is_file() or (p / "index.html").is_file()


def main():
    errors = []
    for rel in REQUIRED:
        if not (DIST / rel).is_file():
            errors.append(f"отсутствует обязательный файл: {rel}")

    checked = 0
    broken = set()
    for html_file in DIST.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8", errors="ignore")
        for href in re.findall(r'(?:href|src)="(/[^"]*)"', content):
            if href.startswith("//"):
                continue
            checked += 1
            if not target_exists(href):
                broken.add(f"{href}  (в {html_file.relative_to(DIST)})")

    for b in sorted(broken):
        errors.append(f"битая внутренняя ссылка: {b}")

    if errors:
        print("ОШИБКИ SMOKE-ПРОВЕРКИ:")
        for e in errors:
            print(" -", e)
        return 1
    print(f"OK: обязательные файлы на месте, внутренних ссылок проверено: {checked}, битых нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
