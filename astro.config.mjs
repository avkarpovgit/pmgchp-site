// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  site: 'https://pmgchp.ru',
  redirects: {
    // раздел переименован: bills → drafts («Проекты НПА»)
    '/monitoring/bills': '/monitoring/drafts',
  },
  integrations: [sitemap()],
});
