import React, { useState } from 'react';
import { Dialog } from '@headlessui/react';
import { changePassword } from '../api'; // Assicurati di avere questa funzione in api.js

export default function PasswordChangeModal({ isOpen, onClose, onLogout }) {
    const [oldPassword, setOldPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [message, setMessage] = useState({ type: '', text: '' });
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage({ type: '', text: '' });

        if (newPassword !== confirmPassword) {
            setMessage({ type: 'error', text: 'Le nuove password non coincidono.' });
            return;
        }

        if (newPassword.length < 8) {
            setMessage({ type: 'error', text: 'La password deve essere di almeno 8 caratteri.' });
            return;
        }

        setLoading(true);
        try {
            await changePassword(oldPassword, newPassword, onLogout);
            setMessage({ type: 'success', text: 'Password cambiata con successo!' });
            setTimeout(() => {
                onClose();
                setOldPassword('');
                setNewPassword('');
                setConfirmPassword('');
                setMessage({ type: '', text: '' });
            }, 1500);
        } catch (err) {
            setMessage({ type: 'error', text: 'Errore: ' + (err.message || 'Controlla la vecchia password') });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onClose={onClose} className="fixed z-50 inset-0 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen px-4">
                <Dialog.Overlay className="fixed inset-0 bg-black opacity-70" />

                <div className="relative bg-gray-800 text-white rounded-lg max-w-sm w-full p-6 shadow-2xl border border-gray-600">
                    <Dialog.Title className="text-xl font-bold mb-4">Cambia Password</Dialog.Title>
                    
                    {message.text && (
                        <div className={`p-2 mb-4 text-sm rounded ${message.type === 'success' ? 'bg-green-800 text-green-100' : 'bg-red-800 text-red-100'}`}>
                            {message.text}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm text-gray-400 mb-1">Vecchia Password</label>
                            <input 
                                type="password" 
                                className="w-full bg-gray-900 border border-gray-700 rounded p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                                value={oldPassword} 
                                onChange={e => setOldPassword(e.target.value)} 
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-gray-400 mb-1">Nuova Password</label>
                            <input 
                                type="password" 
                                className="w-full bg-gray-900 border border-gray-700 rounded p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                                value={newPassword} 
                                onChange={e => setNewPassword(e.target.value)} 
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-gray-400 mb-1">Conferma Nuova Password</label>
                            <input 
                                type="password" 
                                className="w-full bg-gray-900 border border-gray-700 rounded p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                                value={confirmPassword} 
                                onChange={e => setConfirmPassword(e.target.value)} 
                                required
                            />
                        </div>

                        <div className="flex justify-end gap-3 pt-2">
                            <button type="button" onClick={onClose} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm">Annulla</button>
                            <button 
                                type="submit" 
                                disabled={loading}
                                className={`px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded font-bold text-sm ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                            >
                                {loading ? 'Attendere...' : 'Conferma'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </Dialog>
    );
}