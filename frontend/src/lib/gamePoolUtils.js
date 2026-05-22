/** Pool tattici (PV/PA/PS/CHA): UI dedicata in GameTab, non widget consumo. */
export const TACTICAL_POOL_SIGLE = ['PV', 'PA', 'PS', 'CHA'];

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
