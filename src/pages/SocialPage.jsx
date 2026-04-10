import React from 'react';
import { useNavigate } from 'react-router-dom';
import SocialLayout from '../layouts/SocialLayout';
import SocialTab from '../components/SocialTab';

const SocialPage = ({ onLogout }) => {
  const navigate = useNavigate();

  const openMessagesFromSocial = (recipient) => {
    const params = new URLSearchParams();
    params.set('tab', 'messaggi');
    if (recipient?.id) params.set('compose_target_id', String(recipient.id));
    if (recipient?.nome) params.set('compose_target_nome', String(recipient.nome));
    navigate(`/app?${params.toString()}`);
  };

  return (
    <SocialLayout>
      <SocialTab onLogout={onLogout} onOpenMessages={openMessagesFromSocial} />
    </SocialLayout>
  );
};

export default SocialPage;
