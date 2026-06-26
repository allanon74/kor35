import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Compass, Sparkles } from 'lucide-react';

const SocialLayout = ({ children }) => {
  return (
    <div className="h-screen bg-linear-to-b from-[#0f0b13] via-[#1d1020] to-[#0f0b13] text-white overflow-hidden flex flex-col">
      <header className="shrink-0 min-h-14 border-b border-amber-300/25 bg-black/50 backdrop-blur px-3 py-2 flex items-center justify-between gap-2">
        <Link
          to="/app"
          className="inline-flex items-center gap-2 text-sm text-gray-200 hover:text-white shrink-0"
          title="Torna all'area personaggio"
        >
          <ArrowLeft size={16} />
          <span className="hidden sm:inline">Area personaggio</span>
        </Link>
        <Link
          to="/app/start"
          className="inline-flex items-center gap-2 text-amber-200 font-bold tracking-wide hover:text-amber-100 shrink-0"
          title="Torna alla splash page"
        >
          <Sparkles size={16} />
          InstaFame
        </Link>
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-xs text-amber-100/80 hover:text-amber-100 shrink-0"
          title="Apri wiki pubblica"
        >
          <Compass size={14} />
          <span className="hidden sm:inline">Wiki</span>
        </Link>
      </header>
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
};

export default SocialLayout;
