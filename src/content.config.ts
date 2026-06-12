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
    tgId: z.number(),
  }),
});

export const collections = { blog, monitoring };
