import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LogIn, Scroll, BookOpen, Download } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { getMediaUrl, getPublicWikiManualeList, getWikiImageUrl, getWikiManualeLatestPdfUrl } from '../api';
import WidgetChiSiamo from './wg/WidgetChiSiamo';
import WidgetEventi from './wg/WidgetEventi';
import WidgetSocial from './wg/WidgetSocial';

/**
 * Home regolamento — hero brand-first (bosco / ember), senza dashboard clutter.
 */
export default function HomePage({ pageData, siteConfig }) {
  const navigate = useNavigate();
  const { character, isAdmin } = useCharacter();
  const [wikiManuale, setWikiManuale] = useState([]);
  const isLogged = !!character;

  useEffect(() => {
    let cancelled = false;
    getPublicWikiManualeList()
      .then((data) => {
        if (!cancelled && Array.isArray(data)) {
          setWikiManuale(data.filter((m) => m.ultimo_generato_at && m.download_url));
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const isMaintenanceMode = !!siteConfig?.maintenance_mode;
  const maintenanceMessage = String(siteConfig?.maintenance_public_message || '').trim();

  const handleEnter = () => {
    navigate(isLogged ? '/app' : '/login');
  };

  return (
    <div className="wiki-shell min-h-full">
      {/* HERO full-bleed: brand + una riga + CTA */}
      <section className="relative min-h-[70vh] md:min-h-[78vh] w-full overflow-hidden bg-[#140c0a]">
        {pageData?.immagine ? (
          <img
            src={getMediaUrl(pageData.immagine)}
            srcSet={`${getWikiImageUrl('home', 720)} 720w, ${getWikiImageUrl('home', 1100)} 1100w, ${getWikiImageUrl('home', 1400)} 1400w`}
            sizes="100vw"
            alt=""
            width={1400}
            height={900}
            className="wiki-hero-media absolute inset-0 h-full w-full object-cover opacity-80"
            style={{ objectPosition: `center ${pageData.banner_y ?? 40}%` }}
            onError={(e) => {
              e.currentTarget.onerror = null;
              e.currentTarget.removeAttribute('srcset');
              e.currentTarget.src = getMediaUrl(pageData.immagine);
            }}
          />
        ) : (
          <div
            className="absolute inset-0 opacity-90"
            style={{
              background:
                'radial-gradient(ellipse at 30% 20%, #7f1d1d55, transparent 55%), linear-gradient(160deg, #1c100c 0%, #3b1510 45%, #0c0a09 100%)',
            }}
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/55 to-black/25" />

        <div className="relative z-10 flex min-h-[70vh] md:min-h-[78vh] flex-col justify-end px-6 pb-12 pt-20 md:px-12 md:pb-16">
          <div className="flex items-center gap-3 mb-5">
            <img
              src="/Logo Kor-AD_Trasp.png"
              alt=""
              width={56}
              height={56}
              className="h-12 w-12 md:h-14 md:w-14 object-contain drop-shadow-lg"
            />
            <p className="wiki-hero-brand text-3xl md:text-5xl text-white drop-shadow-md">KOR35</p>
          </div>
          <p className="max-w-xl text-base md:text-lg text-stone-200/95 leading-relaxed mb-8">
            LARP forestale: regolamento, ambientazione e ingresso all&apos;app di gioco.
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleEnter}
              className="inline-flex items-center gap-2 rounded-md bg-[var(--wiki-brand)] hover:bg-[var(--wiki-brand-hot)] px-5 py-3 text-sm font-bold uppercase tracking-wide text-white shadow-lg transition-colors"
            >
              <LogIn size={18} aria-hidden="true" />
              {isLogged ? 'Entra nell\'app' : 'Accedi'}
            </button>
            <Link
              to="/regolamento/nuovo"
              className="inline-flex items-center gap-2 rounded-md border border-white/35 bg-black/35 hover:bg-black/50 px-5 py-3 text-sm font-bold uppercase tracking-wide text-white backdrop-blur-sm transition-colors"
            >
              Scopri il mondo
            </Link>
          </div>
        </div>
      </section>

      <div className="max-w-5xl mx-auto px-6 py-10 md:px-10 space-y-10">
        {isMaintenanceMode && (
          <div className="rounded-lg border border-amber-700/40 bg-amber-950/90 p-5 text-amber-50">
            <h3 className="text-lg font-bold mb-1">Maintenance mode attiva</h3>
            <p className="text-sm opacity-95 mb-3">
              {maintenanceMessage || 'Il sistema è temporaneamente in manutenzione.'}
            </p>
            {isAdmin && (
              <button
                type="button"
                onClick={() => navigate('/app/maintenance')}
                className="px-4 py-2 rounded-md bg-amber-500 text-gray-900 font-bold hover:bg-amber-400"
              >
                Apri console maintenance
              </button>
            )}
          </div>
        )}

        <section className="space-y-4">
          <h2 className="wiki-hero-brand text-sm text-[var(--wiki-brand)]">Esplora</h2>
          <div className="grid md:grid-cols-2 gap-3">
            <Link
              to="/regolamento/ambientazione"
              className="flex items-center gap-4 p-5 border border-stone-300/80 bg-white/70 hover:border-[var(--wiki-moss)] transition-colors"
            >
              <Scroll className="text-[var(--wiki-moss)] shrink-0" size={28} aria-hidden="true" />
              <div>
                <h3 className="font-bold text-[var(--wiki-ink)]">Ambientazione</h3>
                <p className="text-sm text-[var(--wiki-muted)]">Mondo e storia</p>
              </div>
            </Link>
            <Link
              to="/regolamento/regolamento"
              className="flex items-center gap-4 p-5 border border-stone-300/80 bg-white/70 hover:border-[var(--wiki-brand)] transition-colors"
            >
              <BookOpen className="text-[var(--wiki-brand)] shrink-0" size={28} aria-hidden="true" />
              <div>
                <h3 className="font-bold text-[var(--wiki-ink)]">Regolamento</h3>
                <p className="text-sm text-[var(--wiki-muted)]">Regole di gioco</p>
              </div>
            </Link>
          </div>
        </section>

        {wikiManuale.length > 0 && (
          <section className="space-y-3">
            <h2 className="wiki-hero-brand text-sm text-[var(--wiki-brand)]">Manuali PDF</h2>
            <div className="grid gap-3 md:grid-cols-2">
              {wikiManuale.map((m) => (
                <a
                  key={m.slug}
                  href={getWikiManualeLatestPdfUrl(m.slug)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 p-4 bg-[var(--wiki-brand)] text-white hover:bg-[var(--wiki-brand-hot)] transition-colors"
                  title={`Scarica ${m.titolo}`}
                >
                  <Download size={22} className="shrink-0" aria-hidden="true" />
                  <div className="min-w-0">
                    <h4 className="font-bold leading-tight">{m.titolo}</h4>
                    {m.sottotitolo && (
                      <p className="text-sm text-white/80 mt-0.5 line-clamp-2">{m.sottotitolo}</p>
                    )}
                  </div>
                </a>
              ))}
            </div>
          </section>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          <WidgetChiSiamo />
          <WidgetEventi />
        </div>
        <WidgetSocial />
      </div>
    </div>
  );
}
