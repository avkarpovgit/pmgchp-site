# pmgchp.ru

Персональный сайт Александра Карпова — юриста по проектному финансированию и ГЧП.

Статический сайт на [Astro](https://astro.build). Деплой — GitHub Actions → GitHub Pages, домен `pmgchp.ru`.

## Структура

- `src/pages/index.astro` — главная
- `src/pages/experience.astro` — опыт
- `src/pages/blog/` — лента блога и шаблон поста
- `src/content/blog/*.md` — посты блога (Markdown)
- `public/images/` — фото и логотипы

## Как добавить пост в блог

Создать файл `src/content/blog/YYMMDD_slug.md`:

```markdown
---
title: Заголовок поста
description: Короткое описание для ленты и SEO
date: 2026-06-11
---

Текст поста в Markdown.
```

После пуша в `main` сайт пересобирается и публикуется автоматически (~2 минуты).

## Локальная разработка

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # production-сборка в dist/
```
