#!/usr/bin/env python3
"""
reg_watch.py — обнаружение новых профильных проектов НПА на regulation.gov.ru.

Зачем: ежедневная сверка статусов (npa-drafts-status-check) проверяет только
ИЗВЕСТНЫЕ карточки по их источникам. Контура обнаружения НОВЫХ проектов не было,
из-за чего 05.08.2026 были пропущены сразу три профильных проекта
(169202 Минфин, 169970 и 169971 Минздрав). Этот скрипт закрывает пробел.

Как работает:
  1. /api/public/Projects?page=N — перечень проектов, новые сверху, по 10 на
     страницу. Отдаёт только id (остальные поля пустые), поэтому используется
     как источник «что появилось».
  2. Идём по страницам, пока не упрёмся в watermark (максимальный id прошлого
     прогона) либо в предохранитель MAX_PAGES.
  3. По каждому новому id — /api/public/PublicProjects/<id> с полными полями.
  4. Фильтруем по ключевым словам, наименованию и основанию разработки.
  5. Проекты, уже заведённые в src/content/drafts (по regId), помечаются как
     известные и в «требует внимания» не попадают.

Состояние — scripts/reg_watch_state.json (watermark + дата прогона).

Использование:
    python3 scripts/reg_watch.py                # обычный прогон
    python3 scripts/reg_watch.py --lookback 300 # разовый прогон вглубь
    python3 scripts/reg_watch.py --dry-run      # не записывать состояние
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://regulation.gov.ru/api/public"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

REPO = Path(__file__).resolve().parent.parent
DRAFTS_DIR = REPO / "src" / "content" / "drafts"
STATE_FILE = Path(__file__).resolve().parent / "reg_watch_state.json"

MAX_PAGES = 40          # предохранитель: 40 стр. * 10 = 400 проектов за прогон
FIRST_RUN_LOOKBACK = 200  # сколько id назад смотреть, если состояния ещё нет
TIMEOUT = 30
RETRIES = 3

# Профильные термины: однозначны, коллизий не дают.
CORE = [
    r"концесси",
    r"государственно-частн",
    r"муниципально-частн",
    r"публично-частн",
    r"защит\w+ и поощрени\w+ капиталовложений",
    r"\bСЗПК\b",
    r"встречн\w+ инвестиционн\w+ обязательств",
    r"\bофсет",
    r"проектн\w+ финансировани",
]

# Номера законов: сами по себе неоднозначны. Номер 115-ФЗ носят и закон о
# концессионных соглашениях, и закон о противодействии отмыванию доходов —
# на этом фильтр ловил проекты ЦБ по ПОД/ФТ (проверено 07.08.2026 на 169982).
# Поэтому номер засчитывается только при отсутствии чужого контекста.
NUMERIC = [
    r"115-ФЗ",
    r"224-ФЗ",
    r"\b69-ФЗ\b",
]

# Чужой контекст для номеров законов.
EXCLUDE = [
    r"легализаци",
    r"отмывани",
    r"финансировани\w* терроризма",
    r"ПОД/ФТ",
]

# Слабые признаки: смежное регулирование. Показываем отдельным списком.
WEAK = [
    r"инфраструктурн\w+ (?:облигаци|кредит|бюджетн)",
    r"Фабрик\w+ проектного финансирования",
    r"инвестиционн\w+ соглашени",
    r"синдицированн\w+ кредит",
    r"ГИИС .Электронный бюджет",
]

CORE_RE = re.compile("|".join(CORE), re.IGNORECASE)
NUMERIC_RE = re.compile("|".join(NUMERIC), re.IGNORECASE)
EXCLUDE_RE = re.compile("|".join(EXCLUDE), re.IGNORECASE)
WEAK_RE = re.compile("|".join(WEAK), re.IGNORECASE)


def fetch(url):
    """GET с ретраями. Возвращает распарсенный JSON либо None."""
    last = None
    for attempt in range(RETRIES):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    print(f"  ! не удалось получить {url}: {last}", file=sys.stderr)
    return None


def known_reg_ids():
    """regId всех карточек в репозитории — и активных, и архивных."""
    ids = set()
    if not DRAFTS_DIR.is_dir():
        return ids
    for f in DRAFTS_DIR.glob("*.md"):
        m = re.search(r'^regId:\s*"?([^"\n]+)"?', f.read_text(encoding="utf-8"), re.M)
        if m:
            ids.add(m.group(1).strip())
    return ids


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("  ! состояние повреждено, считаем прогон первым", file=sys.stderr)
    return {}


def collect_new_ids(watermark):
    """Идём по страницам перечня, собираем id больше watermark."""
    new_ids, page = [], 1
    while page <= MAX_PAGES:
        data = fetch(f"{API}/Projects?page={page}")
        if not data or not data.get("result"):
            break
        ids = [int(x["id"]) for x in data["result"] if str(x.get("id", "")).isdigit()]
        if not ids:
            break
        new_ids.extend(i for i in ids if i > watermark)
        if min(ids) <= watermark:
            break
        page += 1
    else:
        print(
            f"  ! достигнут предел {MAX_PAGES} страниц — возможно, часть проектов "
            f"не просмотрена; прогоните с --lookback побольше",
            file=sys.stderr,
        )
    return sorted(set(new_ids), reverse=True)


def classify(project):
    """Сильное / слабое / мимо — по названию, ключевым словам и основанию."""
    parts = [
        project.get("title") or "",
        project.get("reasonForDevelopment") or "",
        " ".join(k.get("description", "") for k in (project.get("keyWords") or [])),
    ]
    blob = " ".join(parts)
    if CORE_RE.search(blob):
        return "strong"
    if NUMERIC_RE.search(blob) and not EXCLUDE_RE.search(blob):
        return "strong"
    if WEAK_RE.search(blob):
        return "weak"
    return None


def describe(p):
    dep = (p.get("developedDepartment") or {}).get("description", "—")
    kind = (p.get("projectType") or {}).get("description", "—")
    start = (p.get("startPublicDiscussion") or "")[:10]
    end = (p.get("endPublicDiscussion") or "")[:10]
    window = f"{start} — {end}" if start and end else "срок обсуждения не указан"
    return {
        "id": p.get("id"),
        "regId": p.get("projectId") or "",
        "title": re.sub(r"\s+", " ", (p.get("title") or "")).strip(),
        "dep": dep,
        "kind": kind,
        "status": p.get("status"),
        "window": window,
        "end": end,
        "url": f"https://regulation.gov.ru/projects/{p.get('id')}/",
        "reason": re.sub(r"\s+", " ", (p.get("reasonForDevelopment") or "")).strip()[:300],
    }


def report(bucket, title, known):
    if not bucket:
        return
    print(f"\n## {title}\n")
    for r in bucket:
        mark = "  ✓ карточка есть" if r["regId"] in known else "  ⚠ КАРТОЧКИ НЕТ"
        print(f"- **{r['title']}**")
        print(f"  {r['kind']} · {r['dep']} · {r['regId']}")
        print(f"  Обсуждение: {r['window']} · статус: {r['status']}")
        if r["reason"]:
            print(f"  Основание: {r['reason']}")
        print(f"  {r['url']}")
        print(mark)
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback", type=int, default=None,
                    help="разово смотреть N id назад от текущего максимума")
    ap.add_argument("--dry-run", action="store_true", help="не записывать состояние")
    args = ap.parse_args()

    state = load_state()
    known = known_reg_ids()

    head = fetch(f"{API}/Projects?page=1")
    if not head or not head.get("result"):
        print("Не удалось получить перечень проектов — портал недоступен.", file=sys.stderr)
        return 2
    max_id = max(int(x["id"]) for x in head["result"] if str(x.get("id", "")).isdigit())

    if args.lookback is not None:
        watermark = max_id - args.lookback
    elif "watermark" in state:
        watermark = int(state["watermark"])
    else:
        watermark = max_id - FIRST_RUN_LOOKBACK
        print(f"Первый прогон: смотрим {FIRST_RUN_LOOKBACK} проектов назад.")

    print(f"Максимальный id на портале: {max_id}; watermark: {watermark}")
    if state.get("last_run"):
        print(f"Прошлый прогон: {state['last_run']}")

    ids = collect_new_ids(watermark)
    print(f"Новых проектов с прошлого прогона: {len(ids)}")

    strong, weak = [], []
    for n, pid in enumerate(ids, 1):
        p = fetch(f"{API}/PublicProjects/{pid}")
        if not p:
            continue
        verdict = classify(p)
        if verdict == "strong":
            strong.append(describe(p))
        elif verdict == "weak":
            weak.append(describe(p))
        if n % 25 == 0:
            print(f"  … просмотрено {n}/{len(ids)}", file=sys.stderr)

    print(f"\nПрофильных: {len(strong)}; смежных: {len(weak)}")
    report(strong, "Профильные проекты", known)
    report(weak, "Смежные — оценить вручную", known)

    missing = [r for r in strong if r["regId"] not in known]
    if missing:
        print(f"\n**ТРЕБУЕТ ДЕЙСТВИЯ: завести {len(missing)} карточк(и/у).**")
        for r in missing:
            tail = f" — обсуждение до {r['end']}" if r["end"] else ""
            print(f"- {r['regId']}{tail}")
    else:
        print("\nВсе профильные проекты уже заведены.")

    if not args.dry_run:
        STATE_FILE.write_text(
            json.dumps(
                {
                    "watermark": max_id,
                    "last_run": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "checked": len(ids),
                    "strong": len(strong),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"\nСостояние записано: watermark = {max_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
