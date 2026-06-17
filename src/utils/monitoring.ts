import { getCollection } from 'astro:content';
import releases from '../data/monitoring.json';

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
      const lm = line.match(/\[(.+?)\]\((https?:\/\/[^\s")]+)/);
      if (!lm) continue;
      // «вступает/вступают в силу [с] ДД.ММ.ГГГГ» либо вербально «… в силу с 1 сентября 2026»
      let dd = '', mm = '', yyyy = '';
      const numMatch = line.match(/вступа(?:ет|ют) в силу\s+(?:с\s+)?(\d{2})\.(\d{2})\.(\d{4})/);
      const verbMatch = numMatch ? null : line.match(/вступа(?:ет|ют) в силу\s+с\s+(\d{1,2})\s+([а-яё]+)\s+(\d{4})/i);
      if (numMatch) {
        [, dd, mm, yyyy] = numMatch;
      } else if (verbMatch) {
        const mi = MONTHS_RU.indexOf(verbMatch[2].toLowerCase());
        if (mi === -1) continue;
        dd = verbMatch[1].padStart(2, '0');
        mm = String(mi + 1).padStart(2, '0');
        yyyy = verbMatch[3];
      } else {
        continue;
      }
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

export type MonitoringEntry = {
  date: string;
  period: string;
  items: string[];
  slug?: string;
  tgId?: number;
};

type RawRelease = { id: number; date: string; period: string; items: string[] };

/**
 * Единый список выпусков мониторинга (Telegram-лента monitoring.json + выпуски,
 * добавленные вручную как .md), сгруппированный по годам и отсортированный (desc).
 */
export async function getMonitoringByYear(): Promise<{
  years: string[];
  byYear: Map<string, MonitoringEntry[]>;
  currentYear: string;
}> {
  const pages = await getCollection('monitoring');
  const byTgId = new Map<number, string>();
  for (const p of pages) if (p.data.tgId != null) byTgId.set(p.data.tgId, p.id);
  const releaseIds = new Set((releases as RawRelease[]).map((r) => r.id));

  const entries: MonitoringEntry[] = [];
  for (const r of releases as RawRelease[]) {
    entries.push({ date: r.date, period: r.period, items: r.items, slug: byTgId.get(r.id), tgId: r.id });
  }
  for (const p of pages) {
    // выпуск уже учтён через Telegram-ленту — пропускаем
    if (p.data.tgId != null && releaseIds.has(p.data.tgId)) continue;
    const body: string = (p as { body?: string }).body ?? '';
    const items = [...body.matchAll(/^###\s+(.+?)\s*$/gm)].map((m) => m[1].trim());
    entries.push({
      date: p.data.date.toISOString().slice(0, 10),
      period: p.data.period,
      items,
      slug: p.id,
      tgId: p.data.tgId ?? undefined,
    });
  }

  const byYear = new Map<string, MonitoringEntry[]>();
  for (const e of entries) {
    const year = e.date.slice(0, 4);
    if (!byYear.has(year)) byYear.set(year, []);
    byYear.get(year)!.push(e);
  }
  for (const arr of byYear.values()) {
    arr.sort((a, b) => b.date.localeCompare(a.date) || (b.tgId ?? 0) - (a.tgId ?? 0));
  }
  const years = [...byYear.keys()].sort((a, b) => b.localeCompare(a));
  return { years, byYear, currentYear: years[0] };
}
