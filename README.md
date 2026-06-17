# pmgchp.ru

Персональный сайт Александра Карпова — юриста по проектному финансированию и ГЧП,
автора телеграм-канала [«Правовой мониторинг ГЧП»](https://t.me/pmgchp).

Статический сайт на [Astro](https://astro.build) + поиск [Pagefind](https://pagefind.app).
Деплой — GitHub Actions → GitHub Pages (ветка `gh-pages`), домен `pmgchp.ru`.

## Структура

- `src/pages/` — страницы: главная, `monitoring` (архив мониторинга), `news` (новости — еженедельный дайджест),
  `blog` (блог), `experience` (опыт / «Обо мне»), `search` (поиск), `terms` (соглашение), `404`
- `src/content/blog/*.md` — посты блога (Markdown с тегами)
- `src/content/monitoring/*.md` — полные тексты выпусков мониторинга (slug = дата начала недели)
- `src/content/news/*.md` — выпуски раздела «Новости» (еженедельный дайджест по ГЧП; slug = дата)
- `src/content/bills/*.md` — отслеживаемые законопроекты (статусы обновляются с СОЗД)
- `src/data/monitoring.json` — реестр выпусков для страницы архива (id поста в TG, период, оглавление)
- `src/layouts/Base.astro` — общий лейаут: SEO-разметка, тёмная тема, свайп-навигация, Метрика
- `scripts/update_monitoring.py` — автодобавление новых выпусков из веб-версии канала
- `scripts/validate_monitoring.py` — валидатор данных мониторинга (`--fix` удаляет дубли)
- `scripts/update_bills.py` — обновление статусов законопроектов с СОЗД (нужен секрет `DUMA_PROXY`)
- `scripts/check_dist.py` — smoke-проверка собранного `dist/` (обязательные файлы + внутренние ссылки)
- `public/files/` — PDF-документы, `public/images/` — фото и логотипы

## Автоматизация (GitHub Actions)

`.github/workflows/deploy.yml`:

- **пуш в `main`** → валидация данных → сборка (`astro build` + Pagefind) → smoke-check (`check_dist.py`) → деплой в `gh-pages`;
- **ежедневно в 05:00 UTC** → `update_monitoring.py` (новые выпуски мониторинга из канала) и
  `update_bills.py` (статусы законопроектов с СОЗД); изменения автокоммитятся, сайт пересобирается.

## Как добавить пост в блог

Создать `src/content/blog/YYMMDD_slug.md`:

```markdown
---
title: Заголовок
description: Описание для ленты и SEO
date: 2026-06-12
tags: ["концессии"]
---

Текст в Markdown.
```

## Как добавить выпуск мониторинга вручную

1. Добавить запись в начало `src/data/monitoring.json`: `{"id": <id поста в TG>, "date": "YYYY-MM-DD", "period": "...", "items": [...]}`.
2. (Опционально) положить полный текст в `src/content/monitoring/<дата-начала>.md`
   с frontmatter `title`, `period`, `date`, `tgId` — страница появится автоматически,
   архив сошлётся на неё по `tgId`.
3. Проверить: `python3 scripts/validate_monitoring.py`.

## Локальная разработка

```bash
npm install
npm run dev                              # http://localhost:4321 (поиск работает только после build)
npm run build                            # сборка + индекс Pagefind в dist/
python3 scripts/validate_monitoring.py   # проверка данных мониторинга на дубли и дефекты
```

## Лицензия

Авторские материалы сайта (тексты постов и выпусков мониторинга) распространяются по лицензии
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.ru) — подробнее в [LICENSE.md](LICENSE.md)
и в [пользовательском соглашении](https://pmgchp.ru/terms/). Лицензия не распространяется на тексты
нормативных актов и иных официальных документов.
