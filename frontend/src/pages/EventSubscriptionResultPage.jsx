import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, XCircle, Ban } from 'lucide-react';

/**
 * Esito pagamento iscrizione evento (redirect post PayPal o deeplink).
 */
export default function EventSubscriptionResultPage({ onLogout: _onLogout }) {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const esito = String(params.get('esito') || '').toLowerCase();

  let title = 'Esito pagamento';
  let body = '';
  let Icon = XCircle;
  let tone = 'text-amber-200';

  if (esito === 'ok') {
    title = 'Pagamento completato';
    body = 'Iscrizione registrata. Grazie!';
    Icon = CheckCircle2;
    tone = 'text-emerald-200';
  } else if (esito === 'cancellato') {
    title = 'Pagamento annullato';
    body = 'Hai annullato il pagamento PayPal. Nessun addebito è stato effettuato.';
    Icon = Ban;
    tone = 'text-gray-200';
  } else {
    title = 'Pagamento non riuscito';
    body = 'Il pagamento non è stato completato o la conferma è fallita. Riprova dalla start page o contatta lo staff.';
    Icon = XCircle;
    tone = 'text-red-200';
  }

  return (
    <div className="min-h-dvh bg-gray-900 text-white flex flex-col items-center justify-center p-6">
      <div className="max-w-md w-full rounded-xl border border-gray-700 bg-gray-800 p-6 text-center space-y-4">
        <Icon className={`mx-auto ${tone}`} size={48} strokeWidth={1.75} />
        <h1 className="text-xl font-black">{title}</h1>
        <p className="text-sm text-gray-300 leading-relaxed">{body}</p>
        <button
          type="button"
          onClick={() => navigate('/app/start')}
          className="w-full mt-2 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-bold text-sm"
        >
          Torna alla start page
        </button>
      </div>
    </div>
  );
}
