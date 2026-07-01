import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    date: z.coerce.date(),
    draft: z.boolean().default(false),
    tags: z.array(z.string()).default([]),
  }),
});

const monitoring = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/monitoring' }),
  schema: z.object({
    title: z.string(),
    period: z.string(),
    date: z.coerce.date(),
    // tgId есть у выпусков, опубликованных в Telegram. У выпусков, добавленных
    // вручную (ещё не опубликованных в канале), его нет — ссылка «TG ↗» скрывается.
    tgId: z.number().optional(),
  }),
});

const news = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/news' }),
  schema: z.object({
    title: z.string(),
    period: z.string(),
    date: z.coerce.date(),
    // tgId есть у выпусков, опубликованных в Telegram (пост в канале); у черновиков — нет.
    tgId: z.number().optional(),
  }),
});

// Проекты НПА: законопроекты Госдумы, проекты подзаконных актов, указаний ЦБ и т.п.
const drafts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/drafts' }),
  schema: z.object({
    kind: z.string().default('Проект НПА'),    // тип: «Законопроект», «Проект Указания Банка России», …
    number: z.string().optional(),             // номер законопроекта Госдумы, напр. "1254383-8" (если есть)
    regId: z.string().optional(),              // полный ID проекта НПА на regulation.gov.ru, напр. "01/01/02-26/00164852"
    title: z.string(),
    summary: z.string().optional(),            // одна строка для обзора в начале раздела (чему посвящён проект)
    topic: z.string().default('Прочее'),       // тематическая группа для обзора (см. TOPIC_ORDER в drafts.astro)
    date: z.coerce.date(),                     // дата состояния текста / внесения
    status: z.string().default('На рассмотрении'),
    sozd: z.string().url().optional(),         // паспорт на сайте Госдумы (sozd.duma.gov.ru)
    consultant: z.string().url().optional(),   // текст проекта в КонсультантПлюс
    passport: z.string().url().optional(),     // паспорт проекта в КонсультантПлюс
    source: z.string().url().optional(),       // страница проекта (cbr.ru, regulation.gov.ru и т.п.)
    // история прохождения: заполняется вручную по хронологии СОЗД (см. README → «Статусы законопроектов»)
    stages: z.array(z.object({ stage: z.string(), date: z.coerce.date() })).default([]),
    hidden: z.boolean().default(false),        // скрыть из публикации (черновик карточки)
    // Архив: карточка уходит из активного списка на /monitoring/drafts/archive
    // (проект принят как закон либо утратил актуальность).
    archived: z.boolean().default(false),
    lawNumber: z.string().optional(),          // номер принятого закона, напр. "195-ФЗ"
    lawDate: z.coerce.date().optional(),       // дата принятого закона (подписания)
    pravo: z.string().url().optional(),        // официальная публикация на pravo.gov.ru
    lawConsultant: z.string().url().optional(),// текст принятого закона в КонсультантПлюс (base=LAW)
  }),
});

export const collections = { blog, monitoring, news, drafts };
