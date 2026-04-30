import React, { useState } from 'react';
import { GripVertical, Image as ImageIcon } from 'lucide-react';

export default function WikiCoverEditor({ previewUrl, bannerY, onBannerYChange, onImageFileChange }) {
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartY, setDragStartY] = useState(0);
  const [initialBannerY, setInitialBannerY] = useState(50);

  const handleMouseDown = (e) => {
    e.preventDefault();
    setIsDragging(true);
    setDragStartY(e.clientY);
    setInitialBannerY(bannerY || 50);
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    const deltaY = e.clientY - dragStartY;
    const sensitivity = 0.4;

    let newY = initialBannerY - (deltaY * sensitivity);
    if (newY < 0) newY = 0;
    if (newY > 100) newY = 100;
    onBannerYChange(Math.round(newY));
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMiniMapClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickY = e.clientY - rect.top;
    const percentage = (clickY / rect.height) * 100;
    onBannerYChange(Math.max(0, Math.min(100, Math.round(percentage))));
  };

  return (
    <div className="border rounded-lg p-3 bg-gray-50">
      <label className="text-xs font-bold text-gray-700 mb-2 flex justify-between items-center">
        <span>Copertina & Posizionamento</span>
      </label>

      <div className="flex gap-2 h-40">
        <div
          className="flex-1 bg-gray-900 rounded overflow-hidden border border-gray-400 relative group cursor-ns-resize shadow-inner select-none"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {previewUrl ? (
            <>
              <img
                src={previewUrl}
                alt="Anteprima"
                className="w-full h-full object-cover pointer-events-none"
                style={{ objectPosition: `center ${bannerY}%` }}
              />

              <div className="absolute inset-0 pointer-events-none opacity-30">
                <div className="w-full h-1/3 border-b border-white absolute top-0"></div>
                <div className="w-full h-1/3 border-b border-white absolute top-1/3"></div>
                <div className="h-full w-1/3 border-r border-white absolute left-0"></div>
                <div className="h-full w-1/3 border-r border-white absolute left-1/3"></div>
              </div>

              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <div className="bg-black/50 p-1 rounded-full text-white">
                  <GripVertical size={20} />
                </div>
              </div>
            </>
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-gray-400 gap-1">
              <ImageIcon size={24} />
              <span className="text-[10px]">No Img</span>
            </div>
          )}
        </div>

        <div
          className="w-12 bg-gray-200 rounded border border-gray-300 relative overflow-hidden cursor-pointer"
          onClick={handleMiniMapClick}
          title="Clicca per posizionare"
        >
          {previewUrl && (
            <>
              <img
                src={previewUrl}
                alt="Minimap"
                className="w-full h-full object-cover opacity-50"
              />
              <div
                className="absolute w-full h-1/4 border-2 border-yellow-500 bg-yellow-500/20 box-border transition-all duration-75"
                style={{
                  top: `${bannerY}%`,
                  transform: 'translateY(-50%)',
                }}
              ></div>
            </>
          )}
        </div>
      </div>

      <div className="mt-3">
        <input
          type="file"
          accept="image/*"
          onChange={onImageFileChange}
          className="block w-full text-xs text-gray-500 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:bg-indigo-100 file:text-indigo-700"
        />
        <p className="text-[10px] text-gray-500 mt-1">
          Trascina l'immagine a sinistra o clicca sulla barra a destra per regolare il taglio.
        </p>
      </div>
    </div>
  );
}
