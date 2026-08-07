import React, { memo } from 'react';
import {
  ExternalLink,
  Navigation,
  Wrench,
  FlaskConical,
  Monitor,
  Gamepad2,
  LayoutDashboard,
  CreditCard,
  Swords,
  Users,
  Sparkles,
  Shield,
  Home,
} from 'lucide-react';
import {
  StaffToolPageTitle,
  StaffToolShell,
  staffPanelClass,
  staffMutedClass,
} from '../../staff/StaffToolShell';

/**
 * Link relativi alle sezioni/app separate (nuova scheda).
 * Percorsi relativi: Nginx instrada su master/edge senza host assoluti.
 */
const LINK_GROUPS = [
  {
    id: 'pilot',
    title: 'Console pilotaggio',
    description: 'Build dedicata su /pilot/ — apri in kiosk o su tablet di bordo.',
    links: [
      {
        id: 'nav',
        label: 'Navigazione',
        href: '/pilot/',
        hint: 'Plancia principale',
        icon: Navigation,
      },
      {
        id: 'ingegneria',
        label: 'Ingegneria / Compattatore',
        href: '/pilot/?screen=compattatore',
        hint: 'screen=compattatore',
        icon: Wrench,
      },
      {
        id: 'scientifica',
        label: 'Scientifica',
        href: '/pilot/?screen=scientifica',
        hint: 'screen=scientifica',
        icon: FlaskConical,
      },
      {
        id: 'status',
        label: 'Kiosk — stato nave',
        href: '/pilot/?screen=status',
        hint: 'Monitor grande dual-screen',
        icon: Monitor,
      },
      {
        id: 'control',
        label: 'Kiosk — comandi touch',
        href: '/pilot/?screen=control',
        hint: 'Barra touch dual-screen',
        icon: Gamepad2,
      },
      {
        id: 'combined',
        label: 'Combinato (stato + comandi)',
        href: '/pilot/?screen=combined',
        hint: 'Status sopra, plancia sotto — un solo schermo',
        icon: LayoutDashboard,
      },
    ],
  },
  {
    id: 'carte',
    title: 'Piattaforma carte',
    description: 'App Vite separate (stessa sessione staff / giocatore).',
    links: [
      {
        id: 'cardeditor',
        label: 'Card Editor (Studio)',
        href: '/cardeditor/',
        hint: '/cardeditor/',
        icon: CreditCard,
      },
      {
        id: 'cardarena',
        label: 'Card Arena',
        href: '/cardarena/',
        hint: '/cardarena/',
        icon: Swords,
      },
    ],
  },
  {
    id: 'app',
    title: 'App giocatore e social',
    description: 'Shell React principale e InstaFame.',
    links: [
      {
        id: 'start',
        label: 'Hub personaggi',
        href: '/app/start',
        hint: '/app/start',
        icon: Home,
      },
      {
        id: 'play',
        label: 'Play (scheda / gioco)',
        href: '/app/play',
        hint: '/app/play',
        icon: Users,
      },
      {
        id: 'social',
        label: 'InstaFame',
        href: '/app/social',
        hint: '/app/social',
        icon: Sparkles,
      },
    ],
  },
  {
    id: 'sistema',
    title: 'Amministrazione',
    description: 'Pannello Django (stesso host).',
    links: [
      {
        id: 'admin',
        label: 'Django Admin',
        href: '/admin/',
        hint: '/admin/',
        icon: Shield,
      },
    ],
  },
];

function AppLinkCard({ link }) {
  const Icon = link.icon || ExternalLink;
  return (
    <a
      href={link.href}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex items-start gap-3 rounded-xl border border-gray-700 bg-gray-900/50 p-3 transition-colors hover:border-indigo-500/60 hover:bg-gray-800/80"
    >
      <span className="mt-0.5 shrink-0 rounded-lg bg-indigo-900/40 p-2 text-indigo-300 group-hover:bg-indigo-800/50">
        <Icon size={18} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2 font-semibold text-white">
          {link.label}
          <ExternalLink
            size={14}
            className="shrink-0 text-gray-500 opacity-70 group-hover:text-indigo-300"
            aria-hidden
          />
        </span>
        {link.hint ? <span className={`mt-0.5 block font-mono text-[11px] ${staffMutedClass}`}>{link.hint}</span> : null}
      </span>
    </a>
  );
}

/**
 * Hub link a sezioni/app esterne alla dashboard (nuova scheda browser).
 */
function StaffAppLinksPanel() {
  return (
    <StaffToolShell maxWidth="6xl" className="space-y-6">
      <StaffToolPageTitle
        icon={<ExternalLink className="text-sky-400" size={22} />}
        title="Link app"
        description="Apri console pilota, Card Editor e altre sezioni in una nuova scheda (percorsi relativi)."
      />

      {LINK_GROUPS.map((group) => (
        <section key={group.id} className={staffPanelClass}>
          <h3 className="text-sm font-bold uppercase tracking-wide text-violet-300">{group.title}</h3>
          {group.description ? <p className={`mb-3 mt-1 ${staffMutedClass}`}>{group.description}</p> : null}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {group.links.map((link) => (
              <AppLinkCard key={link.id} link={link} />
            ))}
          </div>
        </section>
      ))}
    </StaffToolShell>
  );
}

export default memo(StaffAppLinksPanel);
