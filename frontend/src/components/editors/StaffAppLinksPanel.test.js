import { describe, expect, it } from 'vitest';
import { LINK_GROUPS } from './StaffAppLinksPanel';

function hrefsOf(groupId) {
  const group = LINK_GROUPS.find((g) => g.id === groupId);
  return (group?.links || []).map((link) => link.href);
}

describe('StaffAppLinksPanel', () => {
  it('include selezione, compattatore, scientifica e comunicazioni', () => {
    const all = LINK_GROUPS.flatMap((g) => g.links.map((l) => l.href));
    expect(all).toEqual(expect.arrayContaining([
      '/pilot/?screen=station&viewport=800x480',
      '/pilot/?screen=compattatore',
      '/pilot/?screen=scientifica',
      '/pilot/?screen=comunicazioni',
      '/pilot/?screen=compattatore&viewport=800x480',
      '/pilot/?screen=scientifica&viewport=800x480',
      '/pilot/?screen=comunicazioni&viewport=800x480',
    ]));
  });

  it('la sezione kiosk 800 ha le tre console e la pagina di scelta', () => {
    expect(hrefsOf('station-kiosk')).toEqual([
      '/pilot/?screen=station&viewport=800x480',
      '/pilot/?screen=compattatore&viewport=800x480',
      '/pilot/?screen=scientifica&viewport=800x480',
      '/pilot/?screen=comunicazioni&viewport=800x480',
    ]);
  });
});
