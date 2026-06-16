import { getCollection } from 'astro:content';

/** «23 - 28 марта 2026 г» → «23 — 28 марта 2026» */
export const cleanPeriod = (p: string) =>
  p.replace(/\s*г\.?\s*$/, '').replace(/\s+-\s+/g, ' — ');

export type PendingAct = {
  title: string;
  url: string;
  dateLabel: string;
  iso: string;
  period: string;
  slug: string;
};

const MONTHS_RU = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
];

/**
 * Акты из всех выпусков мониторинга, у которых на строке-ссылке указана дата
 * «вступает в силу ДД.ММ.ГГГГ», ещё не наступившая на момент сборки.
 * Дедуп по номеру документа КонсультантПлюс (n=) + дате, сортировка по дате.
 */
export async function getPendingActs(): Promise<PendingAct[]> {
  const pages = await getCollection('monitoring');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const map = new Map<string, PendingAct>();

  for (const p of pages) {
    const body: string = (p as { body?: string }).body ?? '';
    for (const line of body.split('\n')) {
      const dm = line.match(/вступает в силу\s+(\d{2})\.(\d{2})\.(\d{4})/);
      const lm = line.match(/\[(.+?)\]\((https?:\/\/[^\s")]+)/);
      if (!dm || !lm) continue;
      const [, dd, mm, yyyy] = dm;
      const d = new Date(Number(yyyy), Number(mm) - 1, Number(dd));
      d.setHours(0, 0, 0, 0);
      if (d <= today) continue;
      const iso = `${yyyy}-${mm}-${dd}`;
      const title = lm[1].replace(/[<>]/g, '').trim();
      const url = lm[2];
      const nMatch = url.match(/[?&]n=(\d+)/);
      const key = `${nMatch ? nMatch[1] : title}|${iso}`;
      if (!map.has(key)) {
        map.set(key, {
          title,
          url,
          dateLabel: `${Number(dd)} ${MONTHS_RU[Number(mm) - 1]} ${yyyy}`,
          iso,
          period: cleanPeriod(p.data.period),
          slug: p.id,
        });
      }
    }
  }
  return [...map.values()].sort((a, b) => a.iso.localeCompare(b.iso));
}

/** Русское склонение существительного при числительном. */
export const plural = (n: number, forms: [string, string, string]) => {
  const n10 = n % 10;
  const n100 = n % 100;
  if (n10 === 1 && n100 !== 11) return forms[0];
  if (n10 >= 2 && n10 <= 4 && (n100 < 10 || n100 >= 20)) return forms[1];
  return forms[2];
};
