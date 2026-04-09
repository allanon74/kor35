import GenericHeader from './GenericHeader';
import { LayoutDashboard, Map, Settings, MessageSquare } from 'lucide-react';

const StaffHeader = ({ onLogout, currentTab, onTabChange, rightSlot }) => {
    const staffMenu = [
        { label: 'Plot Management', icon: <Map size={18}/>, active: currentTab === 'plot', action: () => onTabChange('plot') },
        { label: 'Tools Master', icon: <Settings size={18}/>, active: currentTab === 'tools', action: () => onTabChange('tools') },
        { label: 'Messaggi Staff', icon: <MessageSquare size={18}/>, active: currentTab === 'messages', action: () => onTabChange('messages') },
    ];

    return (
        <GenericHeader 
            subtitle="Area Staff / Master" 
            menuItems={staffMenu} 
            rightSlot={rightSlot}
            onLogout={onLogout} 
        />
    );
};