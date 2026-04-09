import React, { useState } from 'react';
import GenericHeader from './GenericHeader';
import Sidebar from './Sidebar';
import { User, Shield, Package, Zap, MessageCircle, Lock } from 'lucide-react';

const PlayerHeader = ({ activeTab, onTabChange, onLogout, charName, charRank, isStaff, onSwitchToMaster }) => {
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    const playerMenuItems = [
        { label: 'Personaggio', icon: <User size={18}/>, active: activeTab === 'home', action: () => onTabChange('home') },
        { label: 'Abilità', icon: <Shield size={18}/>, active: activeTab === 'abilita', action: () => onTabChange('abilita') },
        { label: 'Inventario', icon: <Package size={18}/>, active: activeTab === 'inventory', action: () => onTabChange('inventory') },
        { label: 'Tessiture', icon: <Zap size={18}/>, active: activeTab === 'tessiture', action: () => onTabChange('tessiture') },
        { label: 'Messaggi', icon: <MessageCircle size={18}/>, active: activeTab === 'messaggi', action: () => onTabChange('messaggi') },
    ];

    // Se è staff, aggiungi la voce al menu
    if (isStaff) {
        playerMenuItems.push({ label: '------------', icon: null, action: () => {} });
        playerMenuItems.push({ 
            label: 'Admin Dashboard', 
            icon: <Lock size={18} className="text-red-500"/>, 
            action: onSwitchToMaster 
        });
    }

    return (
        <>
            <GenericHeader 
                subtitle="Area Operativa" 
                onMenuClick={() => setIsMenuOpen(true)}
                rightSlot={
                    <div className="flex items-center gap-3">
                        {isStaff && (
                            <button onClick={onSwitchToMaster} className="hidden md:flex bg-red-900/30 hover:bg-red-900/50 text-red-400 px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wider border border-red-900/50 transition-colors">
                                Master Mode
                            </button>
                        )}
                        <div className="flex flex-col items-end text-[10px] font-bold uppercase tracking-tight">
                            <span className="text-indigo-400">{charName}</span>
                            <span className="text-gray-500">{charRank}</span>
                        </div>
                    </div>
                }
            />
            <Sidebar 
                isOpen={isMenuOpen} 
                onClose={() => setIsMenuOpen(false)} 
                title="Menu Personaggio"
                items={playerMenuItems} 
                onLogout={onLogout} 
            />
        </>
    );
};
export default PlayerHeader;