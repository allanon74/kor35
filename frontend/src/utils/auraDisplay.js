export const getAuraName = (proposal) => {
  if (proposal?.aura_details?.nome) return proposal.aura_details.nome;
  if (proposal?.aura_nome) return proposal.aura_nome;
  if (proposal?.aura && typeof proposal.aura === 'object') {
    return proposal.aura.nome || 'Aura sconosciuta';
  }
  if (proposal?.aura) return `Aura ID ${proposal.aura}`;
  return 'Aura sconosciuta';
};
