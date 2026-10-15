import React from 'react';

export const PNG_PRESENZA_SOCIAL_CAMPI = [
  {
    key: 'tag_instafame',
    label: 'Taggabile su InstaFame',
    hint: 'Compare nei suggerimenti @ di post, commenti e storie.',
  },
  {
    key: 'chiamabile',
    label: 'Può essere chiamato',
    hint: 'Gli altri personaggi possono avviare una chiamata vocale.',
  },
  {
    key: 'destinatario_messaggi',
    label: 'Destinatario di messaggi',
    hint: 'Compare quando qualcuno cerca a chi scrivere. Se ha già scritto lui, si può rispondere.',
  },
  {
    key: 'pubblica_instafame',
    label: 'Può postare su InstaFame',
    hint: 'Può pubblicare post, storie e post nei gruppi. Commenti e like restano comunque disponibili.',
  },
];

export function presenzaSocialToPayload(values) {
  return {
    tag_instafame: values?.tag_instafame !== false,
    chiamabile: values?.chiamabile !== false,
    destinatario_messaggi: values?.destinatario_messaggi !== false,
    pubblica_instafame: values?.pubblica_instafame !== false,
  };
}

export default function PngPresenzaSocialFields({ values, onChange, disabled = false }) {
  return (
    <fieldset className="space-y-2" disabled={disabled}>
      <legend className="text-xs font-bold uppercase tracking-wide text-pink-200 mb-1">
        Presenza social del PnG
      </legend>
      <p className="text-[11px] text-gray-400 leading-snug">
        Vale solo per i personaggi non giocanti. I PG hanno sempre tag, chiamate, messaggi e pubblicazione attivi.
        Commenti, like, chat di gruppo, rubriche e cessioni di oggetti non si disattivano da qui.
      </p>
      {PNG_PRESENZA_SOCIAL_CAMPI.map((campo) => (
        <label
          key={campo.key}
          className="flex items-start gap-3 min-h-11 rounded-lg border border-gray-700 bg-gray-800/70 px-3 py-2 cursor-pointer"
        >
          <input
            type="checkbox"
            className="mt-1 h-5 w-5 shrink-0 accent-pink-500"
            checked={values?.[campo.key] !== false}
            onChange={(e) => onChange(campo.key, e.target.checked)}
          />
          <span className="min-w-0">
            <span className="block text-sm font-semibold text-gray-100 break-words">{campo.label}</span>
            <span className="block text-[11px] text-gray-400 leading-snug">{campo.hint}</span>
          </span>
        </label>
      ))}
    </fieldset>
  );
}
