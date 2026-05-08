import React from 'react';
import { Navigate } from 'react-router-dom';
import { useCharacter } from '../components/CharacterContext';
import MaintenanceModePanel from '../components/MaintenanceModePanel';

export default function MaintenanceConsolePage({ onLogout }) {
  const { isAdmin } = useCharacter();

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <MaintenanceModePanel onLogout={onLogout} />
    </div>
  );
}
