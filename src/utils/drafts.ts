// Тип акта → короткая метка + ранг юридической силы (меньше = выше сила, идёт первым):
// закон/законопроект → постановление Правительства → приказ министерства → указание Банка России.
// Используется в обзоре и карточках проектов НПА (drafts.astro) и в архиве (archive.astro).
export function actMeta(kind: string): { rank: number; short: string } {
  const k = kind.toLowerCase();
  if (k.includes('закон')) return { rank: 1, short: 'Законопроект' };
  if (k.includes('постановлени')) return { rank: 2, short: 'ПП РФ' };
  if (k.includes('приказ')) {
    let short = 'Приказ';
    if (k.includes('минэконом')) short = 'Приказ МЭР';
    else if (k.includes('минфин')) short = 'Приказ Минфина';
    else if (k.includes('минстро')) short = 'Приказ Минстроя';
    else if (k.includes('минтранс')) short = 'Приказ Минтранса';
    return { rank: 3, short };
  }
  if (k.includes('указани')) return { rank: 4, short: 'Указание ЦБ' };
  return { rank: 5, short: kind };
}
