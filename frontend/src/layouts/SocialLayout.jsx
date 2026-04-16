import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Compass, Sparkles } from 'lucide-react';

const SocialLayout = ({ children }) => {
  return (
    <div className="h-screen bg-linear-to-b from-[#0f0b13] via-[#1d1020] to-[#0f0b13] text-white overflow-hidden flex flex-col">
      <header className="shrink-0 h-14 border-b border-amber-300/25 bg-black/50 backdrop-blur px-3 flex items-center justify-between">
        <Link
          to="/app"
          className="inline-flex items-center gap-2 text-sm text-gray-200 hover:text-white"
          title="Torna all'area personaggio"
        >
          <ArrowLeft size={16} />
          Area personaggio
        </Link>
        <Link
          to="/app/start"
          className="inline-flex items-center gap-2 text-amber-200 font-bold tracking-wide hover:text-amber-100"
          title="Torna alla splash page"
        >
          <Sparkles size={16} />
          InstaFame
        </Link>
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-xs text-amber-100/80 hover:text-amber-100"
          title="Apri wiki pubblica"
        >
          <Compass size={14} />
          Wiki
        </Link>
      </header>
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
};

export default SocialLayout;
