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

const bills = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/bills' }),
  schema: z.object({
    number: z.string(),                       // номер законопроекта, напр. "1254383-8"
    title: z.string(),
    date: z.coerce.date(),                     // дата состояния текста / внесения
    status: z.string().default('На рассмотрении'),
    sozd: z.string().url().optional(),         // паспорт на сайте Госдумы (sozd.duma.gov.ru)
    consultant: z.string().url().optional(),   // текст проекта в КонсультантПлюс
    passport: z.string().url().optional(),     // паспорт проекта в КонсультантПлюс
    // история прохождения: обновляется скриптом scripts/update_bills.py по СОЗД
    stages: z.array(z.object({ stage: z.string(), date: z.coerce.date() })).default([]),
    draft: z.boolean().default(false),
  }),
});

export const collections = { blog, monitoring, news, bills };
