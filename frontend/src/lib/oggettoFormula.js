/**
 * Formula d'attacco da mostrare per un oggetto.
 *
 * Il backend espone `attacco_base_effettivo` già svuotato quando l'oggetto non
 * ha formula o quando l'infusione che l'ha generato ha la formula vuota: in quel
 * caso la formula non va resa affatto. Il fallback su `attacco_base` serve agli
 * snapshot offline salvati prima dell'introduzione del campo.
 */
export const formulaAttaccoOggetto = (oggetto) => {
  if (!oggetto) return '';
  if (Object.prototype.hasOwnProperty.call(oggetto, 'attacco_base_effettivo')) {
    return oggetto.attacco_base_effettivo || '';
  }
  return oggetto.attacco_base || '';
};

export default formulaAttaccoOggetto;
