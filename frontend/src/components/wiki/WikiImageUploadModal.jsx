import React from 'react';
import { Upload, X } from 'lucide-react';

export default function WikiImageUploadModal({
  isOpen,
  uploadingImage,
  newImageData,
  newImagePreview,
  onClose,
  onSubmit,
  onImageFileChange,
  setNewImageData,
  resetForm,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/90 z-60 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="p-4 border-b flex justify-between items-center bg-green-50 rounded-t-lg">
          <h3 className="font-bold text-lg text-gray-800 flex items-center gap-2">
            <Upload size={20} className="text-green-600" />
            Carica Nuova Immagine Wiki
          </h3>
          <button
            onClick={() => {
              onClose();
              resetForm();
            }}
            className="text-gray-500 hover:text-red-600 font-bold text-xl px-2"
            disabled={uploadingImage}
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={onSubmit} className="p-4 overflow-y-auto flex-1 space-y-4">
          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">
              Titolo <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={newImageData.titolo}
              onChange={(e) => setNewImageData((prev) => ({ ...prev, titolo: e.target.value }))}
              className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-green-500 outline-none text-sm"
              placeholder="Es: Mappa della città"
              required
              disabled={uploadingImage}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">
              Descrizione (opzionale)
            </label>
            <textarea
              value={newImageData.descrizione}
              onChange={(e) => setNewImageData((prev) => ({ ...prev, descrizione: e.target.value }))}
              className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-green-500 outline-none text-sm"
              rows="3"
              placeholder="Descrizione dell'immagine..."
              disabled={uploadingImage}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">
              Immagine <span className="text-red-500">*</span>
            </label>
            <input
              type="file"
              accept="image/*"
              onChange={onImageFileChange}
              className="block w-full text-xs text-gray-500 file:mr-2 file:py-2 file:px-4 file:rounded file:border-0 file:bg-green-100 file:text-green-700 file:font-bold hover:file:bg-green-200"
              required
              disabled={uploadingImage}
            />
            {newImagePreview && (
              <div className="mt-2 border border-gray-300 rounded p-2 bg-gray-50">
                <img
                  src={newImagePreview}
                  alt="Anteprima"
                  className="max-w-full h-auto max-h-48 mx-auto rounded"
                />
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">
                Larghezza Max (px)
              </label>
              <input
                type="number"
                value={newImageData.larghezza_max}
                onChange={(e) => setNewImageData((prev) => ({ ...prev, larghezza_max: parseInt(e.target.value, 10) || 0 }))}
                className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-green-500 outline-none text-sm"
                min="0"
                placeholder="0 = originale"
                disabled={uploadingImage}
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">
                Allineamento
              </label>
              <select
                value={newImageData.allineamento}
                onChange={(e) => setNewImageData((prev) => ({ ...prev, allineamento: e.target.value }))}
                className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-green-500 outline-none text-sm"
                disabled={uploadingImage}
              >
                <option value="left">Sinistra</option>
                <option value="center">Centro</option>
                <option value="right">Destra</option>
                <option value="full">Larghezza piena</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={() => {
                onClose();
                resetForm();
              }}
              disabled={uploadingImage}
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded font-medium disabled:opacity-50"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={uploadingImage || !newImageData.immagine || !newImageData.titolo.trim()}
              className="px-5 py-2 text-sm bg-green-600 text-white font-bold rounded hover:bg-green-700 shadow disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {uploadingImage && <div className="animate-spin h-3 w-3 border-2 border-white border-t-transparent rounded-full"></div>}
              {uploadingImage ? 'Caricamento...' : 'Carica Immagine'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
