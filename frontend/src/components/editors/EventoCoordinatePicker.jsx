import React, { useCallback, useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Navigation, Search, ClipboardPaste } from 'lucide-react';
import { geocodeEventoLuogo } from '../../api';
import {
  buildNavigatoreLinks,
  hasValidCoordinates,
  normalizeCoordinatesForSave,
  parseCoordinatesFromText,
} from '../../utils/eventoCoordinates';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const DEFAULT_CENTER = { lat: 42.5, lng: 12.5 };
const DEFAULT_ZOOM = 6;
const DETAIL_ZOOM = 14;

function formatCoordInput(value) {
  if (value === null || value === undefined || value === '') return '';
  return String(value);
}

export default function EventoCoordinatePicker({
  latitudine,
  longitudine,
  luogo = '',
  onChange,
  onLogout,
}) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const [pasteValue, setPasteValue] = useState('');
  const [geocodeStatus, setGeocodeStatus] = useState(null);
  const [geocoding, setGeocoding] = useState(false);

  const applyCoordinates = useCallback(
    (lat, lng) => {
      onChange({
        latitudine: lat,
        longitudine: lng,
      });
    },
    [onChange],
  );

  const updateMarker = useCallback((lat, lng) => {
    const map = mapRef.current;
    if (!map) return;
    if (markerRef.current) {
      markerRef.current.setLatLng([lat, lng]);
    } else {
      const marker = L.marker([lat, lng], { draggable: true }).addTo(map);
      marker.on('dragend', () => {
        const pos = marker.getLatLng();
        applyCoordinates(roundCoord(pos.lat), roundCoord(pos.lng));
      });
      markerRef.current = marker;
    }
    map.setView([lat, lng], Math.max(map.getZoom(), DETAIL_ZOOM));
  }, [applyCoordinates]);

  const roundCoord = (n) => Math.round(n * 1e6) / 1e6;

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return undefined;

    const hasCoords = hasValidCoordinates(latitudine, longitudine);
    const startLat = hasCoords ? Number(latitudine) : DEFAULT_CENTER.lat;
    const startLng = hasCoords ? Number(longitudine) : DEFAULT_CENTER.lng;
    const startZoom = hasCoords ? DETAIL_ZOOM : DEFAULT_ZOOM;

    const map = L.map(mapContainerRef.current, {
      center: [startLat, startLng],
      zoom: startZoom,
      scrollWheelZoom: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap',
      maxZoom: 19,
    }).addTo(map);

    map.on('click', (e) => {
      const { lat, lng } = e.latlng;
      applyCoordinates(roundCoord(lat), roundCoord(lng));
    });

    mapRef.current = map;

    if (hasCoords) {
      updateMarker(startLat, startLng);
    }

    const ro = new ResizeObserver(() => {
      map.invalidateSize();
    });
    ro.observe(mapContainerRef.current);

    return () => {
      ro.disconnect();
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!mapRef.current) return;
    if (!hasValidCoordinates(latitudine, longitudine)) {
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
      return;
    }
    updateMarker(Number(latitudine), Number(longitudine));
  }, [latitudine, longitudine, updateMarker]);

  const handleLatChange = (value) => {
    onChange({ latitudine: value, longitudine });
  };

  const handleLngChange = (value) => {
    onChange({ latitudine, longitudine: value });
  };

  const handlePasteApply = () => {
    try {
      const parsed = parseCoordinatesFromText(pasteValue);
      applyCoordinates(parsed.latitudine, parsed.longitudine);
      setGeocodeStatus({ type: 'ok', message: 'Coordinate applicate.' });
    } catch (err) {
      setGeocodeStatus({ type: 'error', message: err.message });
    }
  };

  const handleGeocode = async () => {
    const query = (luogo || '').trim();
    if (!query) {
      setGeocodeStatus({ type: 'error', message: 'Compila prima il campo Luogo dell\'evento.' });
      return;
    }
    setGeocoding(true);
    setGeocodeStatus(null);
    try {
      const data = await geocodeEventoLuogo(query, onLogout);
      applyCoordinates(Number(data.latitudine), Number(data.longitudine));
      setGeocodeStatus({ type: 'ok', message: 'Posizione trovata dal luogo indicato.' });
    } catch (err) {
      setGeocodeStatus({
        type: 'error',
        message: err?.message || 'Nessun risultato per questo indirizzo.',
      });
    } finally {
      setGeocoding(false);
    }
  };

  const handleClear = () => {
    applyCoordinates(null, null);
    setPasteValue('');
    setGeocodeStatus(null);
    if (mapRef.current) {
      mapRef.current.setView([DEFAULT_CENTER.lat, DEFAULT_CENTER.lng], DEFAULT_ZOOM);
    }
  };

  let previewLinks = null;
  try {
    const norm = normalizeCoordinatesForSave(latitudine, longitudine);
    if (norm.latitudine !== null) {
      previewLinks = buildNavigatoreLinks(norm.latitudine, norm.longitudine);
    }
  } catch {
    previewLinks = null;
  }

  return (
    <div className="space-y-4 rounded-lg border border-emerald-800/50 bg-emerald-950/20 p-4">
      <div className="flex items-center gap-2 text-emerald-300">
        <MapPin size={16} />
        <p className="text-[10px] font-black uppercase tracking-widest">Posizione GPS (pubblica)</p>
      </div>
      <p className="text-[11px] text-gray-400 leading-relaxed">
        Inserisci le coordinate manualmente, incollale da Google Maps oppure clicca sulla mappa.
        In database viene salvata una sola coppia lat/lng.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="text-[10px] font-bold text-gray-500 uppercase px-1">Latitudine</label>
          <input
            type="text"
            inputMode="decimal"
            className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700 font-mono text-sm"
            value={formatCoordInput(latitudine)}
            onChange={(e) => handleLatChange(e.target.value)}
            placeholder="es. 45.123456"
          />
        </div>
        <div>
          <label className="text-[10px] font-bold text-gray-500 uppercase px-1">Longitudine</label>
          <input
            type="text"
            inputMode="decimal"
            className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700 font-mono text-sm"
            value={formatCoordInput(longitudine)}
            onChange={(e) => handleLngChange(e.target.value)}
            placeholder="es. 7.654321"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-[10px] font-bold text-gray-500 uppercase px-1">
          Incolla coordinate o link Google Maps
        </label>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            className="flex-1 bg-gray-900 p-3 rounded-lg border border-gray-700 text-sm"
            value={pasteValue}
            onChange={(e) => setPasteValue(e.target.value)}
            placeholder="45.123, 7.456 oppure URL Google Maps"
          />
          <button
            type="button"
            onClick={handlePasteApply}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm font-bold"
          >
            <ClipboardPaste size={16} />
            Applica
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleGeocode}
          disabled={geocoding}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-800 hover:bg-emerald-700 disabled:opacity-50 text-sm font-bold"
        >
          <Search size={16} />
          {geocoding ? 'Ricerca…' : 'Cerca da luogo evento'}
        </button>
        <button
          type="button"
          onClick={handleClear}
          className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm font-bold text-gray-300"
        >
          Azzera coordinate
        </button>
      </div>

      {geocodeStatus && (
        <p className={`text-xs ${geocodeStatus.type === 'error' ? 'text-red-400' : 'text-emerald-400'}`}>
          {geocodeStatus.message}
        </p>
      )}

      <div
        ref={mapContainerRef}
        className="h-56 sm:h-64 w-full rounded-lg border border-gray-700 overflow-hidden z-0"
        aria-label="Mappa per selezione coordinate"
      />

      {previewLinks && (
        <div className="rounded-lg border border-gray-700 bg-gray-900/60 p-3 space-y-2">
          <p className="text-[10px] font-bold text-gray-500 uppercase">Anteprima link navigatore</p>
          <div className="flex flex-wrap gap-2">
            {[
              ['Apri navigatore', previewLinks.geo],
              ['Google Maps', previewLinks.google_maps],
              ['Apple Maps', previewLinks.apple_maps],
              ['Waze', previewLinks.waze],
            ].map(([label, href]) => (
              <a
                key={label}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-400 hover:text-emerald-300 underline"
              >
                <Navigation size={12} />
                {label}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
