export const TAG_SLUGS: Record<string, string> = {
  'концессии': 'kontsessii',
  'СГЧП': 'sgchp',
  'СЗПК': 'szpk',
  'законопроекты': 'zakonoproekty',
  'бюджет': 'byudzhet',
  'облигации': 'obligatsii',
  'судебная практика': 'sudebnaya-praktika',
  'строительство': 'stroitelstvo',
  'закупки': 'zakupki',
  'финансирование': 'finansirovanie',
  'интервью': 'intervyu',
  'события': 'sobytiya',
};

export function tagSlug(tag: string): string {
  return TAG_SLUGS[tag] ?? tag.toLowerCase().replace(/\s+/g, '-');
}

export function slugToTag(slug: string): string | undefined {
  return Object.keys(TAG_SLUGS).find((t) => TAG_SLUGS[t] === slug);
}
