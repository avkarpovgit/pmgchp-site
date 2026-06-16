#!/usr/bin/env python3
"""Ежедневная авто-проверка статуса законопроектов через открытый API Госдумы
(api.duma.gov.ru).

Для каждого файла src/content/bills/*.md берёт номер законопроекта (`number`),
запрашивает у API последнее событие (`lastEvent`), приводит стадию к короткой
подписи и, если она изменилась, обновляет поле `status` и дописывает запись в
историю `stages` (с датой события).

Требуется токен приложения API Госдумы в переменной окружения DUMA_API_TOKEN
(регистрируется бесплатно на api.duma.gov.ru, хранится как секрет репозитория).

Fail-safe: нет токена / API недоступен / не распознали стадию / нет PyYAML →
файл НЕ меняется, скрипт завершается с кодом 0 (сборка не падает). `status`
всегда можно поправить вручную.

ВНИМАНИЕ по доступности: api.duma.gov.ru, судя по проверкам, отклоняет
TCP-соединения с зарубежных IP. Если GitHub Actions не сможет достучаться,
задайте секрет DUMA_PROXY (http-прокси с российским IP) — скрипт пойдёт через
него. Лог шага покажет, удалось ли соединение.

Запуск:  python3 scripts/update_bills.py [--selftest]
Селф-тест проверяет нормализацию стадий и не требует сети/токена/PyYAML.
"""
import os
import sys
import re
import json
import datetime
import pathlib
import urllib.request
import urllib.parse

try:
    import yaml
except ImportError:
    yaml = None

BILLS_DIR = pathlib.Path(__file__).parent.parent / "src" / "content" / "bills"
API_HOST = "http://api.duma.gov.ru"

# Стадии прохождения от наиболее продвинутой к наименее. lastEvent описывает
# ТЕКУЩЕЕ состояние (а не список будущих стадий), поэтому достаточно сопоставить
# текст фазы/решения с шаблонами и взять первое (самое продвинутое) совпадение.
STAGES = [
    (r"опубликован|вступил[аи]?\s+в\s+силу", "Опубликован"),
    (r"у\s+президента|подписан[ие]*\s+президентом", "У Президента"),
    (r"совет[еа]?\s+федерации", "В Совете Федерации"),
    (r"треть[а-я]*\s+чтени|в\s+третьем\s+чтении", "III чтение"),
    (r"втор[а-я]*\s+чтени|во\s+втором\s+чтении", "II чтение"),
    (r"перв[а-я]*\s+чтени|в\s+первом\s+чтении", "I чтение"),
    (r"предварительн|совет[а-я]*\s+(?:государственной\s+думы|гд)\b", "У Совета Госдумы"),
    (r"внесен|внесение", "Внесён в Госдуму"),
]


def _opener():
    proxy = os.environ.get("DUMA_PROXY")
    if proxy:
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        return urllib.request.build_opener(handler)
    return urllib.request.build_opener()


def fetch_law(number, token):
    """Запрос законопроекта по номеру. Возвращает dict закона или None."""
    qs = urllib.parse.urlencode({"number": number})
    url = f"{API_HOST}/api/{token}/search.json?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "pmgchp-site/1.0"})
    raw = _opener().open(req, timeout=45).read().decode("utf-8", "replace")
    data = json.loads(raw)
    laws = data.get("laws") or data.get("bills") or []
    if not laws:
        return None
    norm = number.replace(" ", "")
    for law in laws:
        if str(law.get("number", "")).replace(" ", "") == norm:
            return law
    return laws[0]


def status_from_event(event):
    """lastEvent (dict) → короткая подпись стадии или None."""
    parts = []
    for key in ("phase", "stage"):
        v = event.get(key)
        if isinstance(v, dict):
            parts.append(v.get("name", "") or "")
        elif isinstance(v, str):
            parts.append(v)
    parts.append(event.get("solution", "") or "")
    parts.append(event.get("name", "") or "")
    text = " ".join(p for p in parts if p)
    for pat, label in STAGES:
        if re.search(pat, text, re.I):
            return label
    return None


def event_date(event, today):
    """Дата события для истории: ISO или ДД.ММ.ГГГГ из lastEvent, иначе сегодня."""
    raw = (event.get("date") or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})", raw)
    if m:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return today


def split_frontmatter(txt):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", txt, re.S)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def process_file(path, token, today):
    raw = path.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(raw)
    if fm_text is None:
        print(f"  {path.name}: нет frontmatter — пропуск")
        return False
    data = yaml.safe_load(fm_text) or {}
    number = str(data.get("number") or "").strip()
    if not number:
        print(f"  {path.name}: нет номера законопроекта — пропуск")
        return False
    try:
        law = fetch_law(number, token)
    except Exception as e:  # сеть/таймаут/блокировка/токен — файл не трогаем
        print(f"  {path.name}: API недоступен или ошибка запроса ({e}) — без изменений")
        return False
    if not law or not isinstance(law.get("lastEvent"), dict):
        print(f"  {path.name}: нет данных lastEvent в ответе API — без изменений")
        return False
    event = law["lastEvent"]
    new_status = status_from_event(event)
    if not new_status:
        print(f"  {path.name}: стадию не распознали ({event.get('phase')}) — без изменений")
        return False
    old_status = (data.get("status") or "").strip()
    if new_status == old_status:
        print(f"  {path.name}: без изменений ({old_status})")
        return False
    data["status"] = new_status
    stages = data.get("stages") or []
    stages.append({"stage": new_status, "date": event_date(event, today)})
    data["stages"] = stages
    new_fm = yaml.safe_dump(
        data, allow_unicode=True, sort_keys=False, default_flow_style=False
    ).rstrip("\n")
    path.write_text(f"---\n{new_fm}\n---\n{body}", encoding="utf-8")
    print(f"  {path.name}: {old_status!r} -> {new_status!r} (обновлено)")
    return True


def main():
    token = os.environ.get("DUMA_API_TOKEN", "").strip()
    if not token:
        print("DUMA_API_TOKEN не задан — обновление статусов пропущено")
        return 0
    if yaml is None:
        print("PyYAML не установлен — обновление статусов пропущено")
        return 0
    if not BILLS_DIR.exists():
        print("каталог законопроектов не найден — пропуск")
        return 0
    if os.environ.get("DUMA_PROXY"):
        print("используется прокси DUMA_PROXY")
    today = datetime.date.today()
    files = sorted(BILLS_DIR.glob("*.md"))
    print(f"законопроектов: {len(files)}")
    changed = 0
    for f in files:
        try:
            if process_file(f, token, today):
                changed += 1
        except Exception as e:
            print(f"  {f.name}: ошибка обработки ({e}) — пропуск")
    print(f"обновлено: {changed}")
    return 0


# --- Селф-тест: нормализация стадий из lastEvent (без сети/токена/PyYAML) ---
def selftest():
    cases = [
        ({"phase": {"name": "Внесение законопроекта в Государственную Думу"}}, "Внесён в Госдуму"),
        ({"phase": {"name": "Предварительное рассмотрение законопроекта, внесенного в Государственную Думу"}}, "У Совета Госдумы"),
        ({"phase": {"name": "Рассмотрение законопроекта в первом чтении"}, "solution": "принять в первом чтении"}, "I чтение"),
        ({"phase": {"name": "Рассмотрение законопроекта во втором чтении"}}, "II чтение"),
        ({"phase": {"name": "Рассмотрение законопроекта в третьем чтении"}}, "III чтение"),
        ({"phase": {"name": "Прохождение закона в Совете Федерации Федерального Собрания Российской Федерации"}}, "В Совете Федерации"),
        ({"phase": {"name": "Прохождение закона у Президента Российской Федерации"}}, "У Президента"),
        ({"phase": {"name": "Опубликование закона"}}, "Опубликован"),
        ({"phase": {"name": "Нечто непонятное"}}, None),
    ]
    for ev, expected in cases:
        got = status_from_event(ev)
        assert got == expected, f"для {ev.get('phase')}: ожидалось {expected!r}, получено {got!r}"
    assert event_date({"date": "2026-06-13"}, datetime.date(2026, 1, 1)) == datetime.date(2026, 6, 13)
    assert event_date({"date": "13.06.2026"}, datetime.date(2026, 1, 1)) == datetime.date(2026, 6, 13)
    assert event_date({}, datetime.date(2026, 1, 1)) == datetime.date(2026, 1, 1)
    print("selftest OK: нормализация стадий и разбор даты события работают")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
