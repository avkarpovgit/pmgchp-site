#!/usr/bin/env python3
"""Валидатор src/data/monitoring.json. Возвращает ненулевой код при дефектах данных.

Проверки: уникальность id, непустые period/date, корректная дата,
отсутствие дублей в items внутри выпуска, сортировка по id по убыванию.
Запуск: python3 scripts/validate_monitoring.py [--fix]  (--fix удаляет дубли items)
"""
import json
import re
import sys
import pathlib

DATA = pathlib.Path(__file__).parent.parent / "src/data/monitoring.json"


def norm(s):
    return " ".join(s.split()).lower()


def main():
    fix = "--fix" in sys.argv
    releases = json.load(open(DATA))
    errors = []
    seen_ids = set()
    prev_id = None

    for e in releases:
        rid = e.get("id")
        if not isinstance(rid, int):
            errors.append(f"id не число: {rid!r}")
            continue
        if rid in seen_ids:
            errors.append(f"дубль id: {rid}")
        seen_ids.add(rid)
        if prev_id is not None and rid > prev_id:
            errors.append(f"нарушена сортировка по id (по убыванию): {rid} после {prev_id}")
        prev_id = rid

        if not e.get("period", "").strip():
            errors.append(f"id {rid}: пустой period")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", e.get("date", "")):
            errors.append(f"id {rid}: некорректная дата {e.get('date')!r}")

        items = e.get("items", [])
        normed = [norm(i) for i in items]
        if len(normed) != len(set(normed)):
            if fix:
                seen, clean = set(), []
                for i in items:
                    k = norm(i)
                    if k not in seen:
                        seen.add(k)
                        clean.append(i)
                e["items"] = clean
                print(f"id {rid} ({e['period']}): удалено дублей items: {len(items) - len(clean)}")
            else:
                errors.append(f"id {rid} ({e['period']}): дубли в items")

    if fix:
        json.dump(releases, open(DATA, "w"), ensure_ascii=False, indent=1)

    if errors:
        print("ОШИБКИ ДАННЫХ МОНИТОРИНГА:")
        for err in errors:
            print(" -", err)
        return 1
    print(f"OK: {len(releases)} выпусков, дефектов не найдено")
    return 0


if __name__ == "__main__":
    sys.exit(main())
