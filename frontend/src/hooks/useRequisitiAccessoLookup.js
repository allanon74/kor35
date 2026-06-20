import { useEffect, useMemo, useState } from 'react';
import {
  getPunteggiList,
  getStatisticheList,
  staffGetAbilitaListAll,
  staffGetCariche,
  staffGetCarriere,
  staffGetKorps,
} from '../api';

const emptyLookup = () => ({
  abilita: [],
  korps: [],
  carriere: [],
  cariche: [],
  statistiche: [],
  auras: [],
});

/**
 * Carica elenchi per combobox requisiti (statistiche, aure, abilità, KORP, …).
 */
export function useRequisitiAccessoLookup(onLogout, merge = {}) {
  const [loaded, setLoaded] = useState(emptyLookup);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      getStatisticheList(onLogout),
      getPunteggiList(onLogout),
      staffGetKorps(onLogout),
      staffGetCarriere(onLogout),
      staffGetCariche(onLogout),
      staffGetAbilitaListAll(onLogout, { pageSize: 500 }),
    ])
      .then(([stats, punteggi, korps, carriere, cariche, abilita]) => {
        if (cancelled) return;
        const pList = Array.isArray(punteggi) ? punteggi : punteggi?.results || [];
        setLoaded({
          statistiche: Array.isArray(stats) ? stats : stats?.results || [],
          auras: pList.filter((p) => p.tipo === 'AU'),
          korps: Array.isArray(korps) ? korps : korps?.results || [],
          carriere: Array.isArray(carriere) ? carriere : carriere?.results || [],
          cariche: Array.isArray(cariche) ? cariche : cariche?.results || [],
          abilita: Array.isArray(abilita) ? abilita : [],
        });
      })
      .catch(console.error)
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [onLogout]);

  const lookup = useMemo(
    () => ({
      ...loaded,
      ...merge,
      abilita: merge.abilita?.length ? merge.abilita : loaded.abilita,
      korps: merge.korps?.length ? merge.korps : loaded.korps,
      carriere: merge.carriere?.length ? merge.carriere : loaded.carriere,
      cariche: merge.cariche?.length ? merge.cariche : loaded.cariche,
    }),
    [loaded, merge],
  );

  return { lookup, loading };
}

export default useRequisitiAccessoLookup;
