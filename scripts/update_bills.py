#!/usr/bin/env python3
"""Ежедневная авто-проверка статуса законопроектов по странице СОЗД
(sozd.duma.gov.ru) — система обеспечения законодательной деятельности.

Открытый API api.duma.gov.ru для этого непригоден: его датасет заморожен на
~февраль 2025 (законов 2026 г. там нет). СОЗД же — живой server-rendered HTML
без токена/Referer/прокси.

Для каждого файла src/content/bills/*.md берёт номер законопроекта (`number`),
скачивает sozd.duma.gov.ru/bill/<number>, определяет текущую стадию как самое
продвинутое ДАТИРОВАННОЕ решение из хронологии и, если стадия изменилась,
обновляет поле `status` и дописывает запись в историю `stages`.

Почему «датированное»: на странице есть и трекер будущих стадий (без дат) — он
игнорируется; учитываются только уже состоявшиеся события, у которых рядом стоит
дата ДД.ММ.ГГГГ. А привязка к словам-решениям («принять… в первом чтении»,
«направить в Совет Федерации») отсекает упоминания других НПА в тексте.

Fail-safe: сеть/парсинг/без PyYAML → файл НЕ меняется, код возврата 0 (сборка не
падает). `status` всегда можно поправить вручную. Если СОЗД когда-нибудь
заблокирует раннер — задайте секрет DUMA_PROXY (http-прокси с РФ-IP).

Запуск:  python3 scripts/update_bills.py [--selftest]
Селф-тест проверяет detect_status на фикстуре, сеть/PyYAML не нужны.
"""
import os
import sys
import re
import html
import datetime
import pathlib
import urllib.request
import urllib.parse

try:
    import yaml
except ImportError:
    yaml = None

BILLS_DIR = pathlib.Path(__file__).parent.parent / "src" / "content" / "bills"
SOZD_URL = "https://sozd.duma.gov.ru/bill/{number}"

# Решения из хронологии СОЗД от наиболее продвинутого к наименее. Подпись —
# короткая, для бейджа. Для стадий-чтений требуем слово «принят», чтобы не
# спутать состоявшееся чтение с лишь назначенным на будущую дату.
STAGES = [
    (r"вступил[аи]?\s+в\s+силу|закон\s+опубликован|официальн\w*\s+опубликован", "Опубликован"),
    (r"подписан[ао]?\s+президентом|подписан\s+федеральный\s+закон", "Подписан Президентом"),
    (r"одобр\w+\s+совет\w*\s+федерации", "Одобрен Советом Федерации"),
    (r"направ\w+\s+(?:закон\s+|законопроект\s+)?в\s+совет\s+федерации|рассмотрени\w+\s+советом\s+федерации", "Направлен в Совет Федерации"),
    (r"принят\w*\s+(?:закон|(?:законопроект\s+)?(?:в\s+)?треть\w+\s+чтени)|одобрить\s+закон", "Принят Госдумой"),
    (r"принят\w*\s+(?:законопроект\s+)?(?:во\s+)?втор\w+\s+чтени", "Принят во II чтении"),
    (r"принят\w*\s+(?:законопроект\s+)?(?:в\s+)?перв\w+\s+чтени", "Принят в I чтении"),
    (r"предварительн\w*\s+рассмотрени|назначить\s+ответственн|ответственн\w+\s+комитет", "У Совета Госдумы"),
    (r"внесен\w*\s+в\s+государственную\s+думу|зарегистрирован\w*\s+и\s+направлен", "Внесён в Госдуму"),
]
DATE_RE = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")


def _opener():
    proxy = os.environ.get("DUMA_PROXY")
    if proxy:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
    return urllib.request.build_opener()


def fetch(number):
    url = SOZD_URL.format(number=urllib.parse.quote(number))
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; pmgchp-site/1.0)",
        "Accept-Language": "ru",
    })
    return _opener().open(req, timeout=60).read().decode("utf-8", "replace")


def to_text(page_html):
    t = html.unescape(re.sub(r"<[^>]+>", " ", page_html))
    return re.sub(r"\s+", " ", t)


def detect_status(page_html):
    """(подпись стадии, дата ДД.ММ.ГГГГ) или (None, None).

    Берём самое продвинутое решение, рядом с которым (±90 символов) есть дата —
    т.е. событие действительно состоялось, а не просто перечислено в трекере.
    """
    text = to_text(page_html)
    for pat, label in STAGES:
        for m in re.finditer(pat, text, re.I):
            window = text[max(0, m.start() - 90): m.end() + 90]
            dm = DATE_RE.search(window)
            if dm:
                return label, dm.group(0)
    return None, None


def parse_date(s, today):
    m = DATE_RE.match(s) if s else None
    if not m:
        return today
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return today


def split_frontmatter(txt):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", txt, re.S)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def process_file(path, today):
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
        page = fetch(number)
    except Exception as e:  # сеть/таймаут/блокировка — файл не трогаем
        print(f"  {path.name}: СОЗД недоступен ({e}) — без изменений")
        return False
    new_status, when = detect_status(page)
    if not new_status:
        print(f"  {path.name}: стадию на странице СОЗД не распознали ({len(page)} байт) — без изменений")
        return False
    print(f"  {path.name}: СОЗД → {new_status!r} (событие {when})")
    old_status = (data.get("status") or "").strip()
    if new_status == old_status:
        return False
    data["status"] = new_status
    stages = data.get("stages") or []
    stages.append({"stage": new_status, "date": parse_date(when, today)})
    data["stages"] = stages
    new_fm = yaml.safe_dump(
        data, allow_unicode=True, sort_keys=False, default_flow_style=False, width=4096
    ).rstrip("\n")
    path.write_text(f"---\n{new_fm}\n---\n{body}", encoding="utf-8")
    print(f"  {path.name}: {old_status!r} -> {new_status!r} (обновлено)")
    return True


def main():
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
            if process_file(f, today):
                changed += 1
        except Exception as e:
            print(f"  {f.name}: ошибка обработки ({e}) — пропуск")
    print(f"обновлено: {changed}")
    return 0


# --- Селф-тест: detect_status по фикстуре хронологии (без сети/PyYAML) ---
FIXTURE_FULL = """
<ul class="tracker"><li>Внесение</li><li>Предварительное рассмотрение</li>
<li>Рассмотрение в первом чтении</li><li>Рассмотрение во втором чтении</li>
<li>Рассмотрение в третьем чтении</li><li>Прохождение закона в Совете Федерации</li></ul>
<div id="hron">
08.06.2026 Внесён в Государственную Думу, зарегистрирован и направлен Председателю ГД.
09.06.2026 Назначить ответственный комитет.
10.06.2026 Принять законопроект в первом чтении.
10.06.2026 Принять закон.
10.06.2026 Направить закон в Совет Федерации.
</div>
"""
FIXTURE_EARLY = """
<ul class="tracker"><li>Рассмотрение в первом чтении</li></ul>
<div id="hron">08.06.2026 Внесён в Государственную Думу. 09.06.2026 Назначить ответственный комитет.</div>
"""


def selftest():
    s, d = detect_status(FIXTURE_FULL)
    assert s == "Направлен в Совет Федерации", f"FULL: {s!r}"
    assert d == "10.06.2026", f"FULL date: {d!r}"
    s2, _ = detect_status(FIXTURE_EARLY)
    assert s2 == "У Совета Госдумы", f"EARLY: {s2!r}"  # «первом чтении» без даты — игнор
    s3, _ = detect_status("<div>нет ни дат, ни решений</div>")
    assert s3 is None, f"EMPTY: {s3!r}"
    assert parse_date("10.06.2026", datetime.date(2000, 1, 1)) == datetime.date(2026, 6, 10)
    print("selftest OK: detect_status берёт самое продвинутое датированное решение")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
