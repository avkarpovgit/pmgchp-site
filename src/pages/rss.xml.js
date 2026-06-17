import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const blog = (await getCollection('blog', ({ data }) => !data.draft)).map((p) => ({
    title: p.data.title,
    description: p.data.description ?? '',
    pubDate: p.data.date,
    link: `/blog/${p.id}/`,
  }));

  const news = (await getCollection('news')).map((p) => ({
    title: p.data.title,
    description: `Дайджест новостей по ГЧП и проектному финансированию за ${p.data.period}.`,
    pubDate: p.data.date,
    link: `/news/${p.id}/`,
  }));

  const monitoring = (await getCollection('monitoring')).map((p) => ({
    title: p.data.title,
    description: `Правовой мониторинг ГЧП за ${p.data.period}.`,
    pubDate: p.data.date,
    link: `/monitoring/${p.id}/`,
  }));

  // Единый фид: блог + новости + мониторинг, свежие сверху, последние 50 материалов
  const items = [...blog, ...news, ...monitoring]
    .sort((a, b) => b.pubDate.valueOf() - a.pubDate.valueOf())
    .slice(0, 50);

  return rss({
    title: 'Правовой мониторинг ГЧП — Александр Карпов',
    description: 'Новости, статьи и обзоры по ГЧП, концессиям и проектному финансированию.',
    site: context.site,
    items,
    customData: '<language>ru</language>',
  });
}
