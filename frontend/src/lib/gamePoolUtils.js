/** Pool tattici (PV/PA/PS/CHA): UI dedicata in GameTab, non widget consumo. */
export const TACTICAL_POOL_SIGLE = ['PV', 'PA', 'PS', 'CHA'];

/**
 * Valore corrente di un pool tattico per Status Fisico / Chakra in GameTab.
 * Non usare {@link risorsePoolVisibiliInGame}: i tattici sono esclusi da quella lista.
 */
export function getTacticalPoolCurrent(char, sigla, legacyTempKey, maxFallback = 0) {
    if (!char) return maxFallback;
    const s = String(sigla || '').toUpperCase();
    const pools = char.risorse_pool_ui || [];
    const row = pools.find((p) => String(p?.sigla || '').toUpperCase() === s);
    if (row != null && row.valore_corrente != null) {
        return row.valore_corrente;
    }
    const rc = char.risorse_consumabili || {};
    if (rc[s] !== undefined && rc[s] !== null) {
        return rc[s];
    }
    const prim = (char.statistiche_primarie || []).find(
        (x) => String(x?.sigla || '').toUpperCase() === s
    );
    if (prim?.valore_corrente != null) {
        return prim.valore_corrente;
    }
    const temp = char.statistiche_temporanee || {};
    if (legacyTempKey && temp[legacyTempKey] != null) {
        return temp[legacyTempKey];
    }
    if (s === 'CHA' && temp.CHK_CUR != null) {
        return temp.CHK_CUR;
    }
    return maxFallback;
}

/**
 * Risorse pool mostrabili in scheda Gioco: massimo di scheda > 0, esclusi i tattici.
 * @param {Array<{ sigla?: string, valore_max?: number }>} pools
 */
export function risorsePoolVisibiliInGame(pools) {
    return (pools || []).filter(
        (p) =>
            Number(p?.valore_max) > 0 &&
            !TACTICAL_POOL_SIGLE.includes(String(p?.sigla || '').toUpperCase())
    );
}
