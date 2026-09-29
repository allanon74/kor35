import React, { useState, useEffect, useRef, useMemo, memo } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, X, Check } from 'lucide-react';
import { useDebounce } from '../../hooks/useDebounce';

/** Sotto questa soglia si usa un `<select>` nativo (liste corte, UX più immediata). */
export const DEFAULT_MIN_OPTIONS_FOR_SEARCH = 12;

/** Sopra modali staff (z-[100]) e toast (z-[100]). */
export const SEARCHABLE_DROPDOWN_Z_CLASS = 'z-[110]';

const NativeSelect = memo(({
    options = [],
    value,
    onChange,
    placeholder = 'Seleziona...',
    labelKey = 'nome',
    valueKey = 'id',
    disabled = false,
    className = '',
}) => {
    const sorted = useMemo(
        () =>
            [...options].sort((a, b) =>
                String(a[labelKey] || '').localeCompare(String(b[labelKey] || ''))
            ),
        [options, labelKey]
    );

    return (
        <select
            className={`w-full min-h-11 bg-gray-950 border border-gray-700 rounded px-2 py-2 text-sm text-white outline-none focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
            value={value === null || value === undefined ? '' : String(value)}
            disabled={disabled}
            onChange={(e) => {
                const v = e.target.value;
                if (v === '') {
                    onChange(null);
                    return;
                }
                // UUID (modelli sync) e stringhe: non parseInt
                if (/^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(v)) {
                    onChange(v);
                    return;
                }
                const parsed = parseInt(v, 10);
                onChange(Number.isNaN(parsed) ? v : parsed);
            }}
        >
            <option value="">{placeholder}</option>
            {sorted.map((opt) => (
                <option key={opt[valueKey]} value={String(opt[valueKey])}>
                    {opt[labelKey]}
                </option>
            ))}
        </select>
    );
});

NativeSelect.displayName = 'NativeSelect';

const SearchableDropdown = memo(({
    options = [],
    value,
    onChange,
    placeholder = 'Seleziona...',
    labelKey = 'nome',
    valueKey = 'id',
    disabled = false,
    /** Sopra StaffEditorModal (z-[100]) e altri overlay staff. */
    dropdownZIndex = 110,
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0, maxHeight: 240 });
    const [uniqueId] = useState(() => `searchable-${Math.random().toString(36).substr(2, 9)}`);
    const wrapperRef = useRef(null);
    const triggerRef = useRef(null);

    const debouncedSearchTerm = useDebounce(searchTerm, 200);

    const selectedItem = useMemo(
        () => options.find((opt) => String(opt[valueKey]) === String(value)),
        [options, value, valueKey]
    );

    const filteredOptions = useMemo(() => {
        return options
            .filter((opt) => {
                const label = opt[labelKey] || '';
                return label.toLowerCase().includes(debouncedSearchTerm.toLowerCase());
            })
            .sort((a, b) => (a[labelKey] || '').localeCompare(b[labelKey] || ''));
    }, [options, debouncedSearchTerm, labelKey]);

    useEffect(() => {
        const handlePointerOutside = (event) => {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
                const dropdownElement = document.getElementById(`dropdown-${uniqueId}`);
                if (!dropdownElement || !dropdownElement.contains(event.target)) {
                    setIsOpen(false);
                }
            }
        };
        // pointerdown copre mouse + touch (telefono): mousedown da solo è inaffidabile su mobile
        document.addEventListener('pointerdown', handlePointerOutside);
        return () => document.removeEventListener('pointerdown', handlePointerOutside);
    }, [uniqueId]);

    useEffect(() => {
        if (!isOpen) setSearchTerm('');
    }, [isOpen]);

    useEffect(() => {
        if (isOpen && triggerRef.current) {
            const updatePosition = () => {
                const rect = triggerRef.current.getBoundingClientRect();
                // position:fixed → coordinate viewport (NO scrollY/scrollX), altrimenti
                // dopo scroll della form staff il menu finisce fuori schermo sul telefono.
                const gap = 4;
                const maxMenuHeight = 240; // max-h-60
                const spaceBelow = window.innerHeight - rect.bottom - gap;
                const spaceAbove = rect.top - gap;
                const openUpwards = spaceBelow < Math.min(maxMenuHeight, 160) && spaceAbove > spaceBelow;
                const left = Math.max(8, Math.min(rect.left, window.innerWidth - rect.width - 8));
                if (openUpwards) {
                    setDropdownPosition({
                        bottom: window.innerHeight - rect.top + gap,
                        left,
                        width: rect.width,
                        maxHeight: Math.max(120, Math.min(maxMenuHeight, spaceAbove)),
                    });
                } else {
                    setDropdownPosition({
                        top: rect.bottom + gap,
                        left,
                        width: rect.width,
                        maxHeight: Math.max(120, Math.min(maxMenuHeight, spaceBelow)),
                    });
                }
            };

            updatePosition();

            window.addEventListener('scroll', updatePosition, true);
            window.addEventListener('resize', updatePosition);

            return () => {
                window.removeEventListener('scroll', updatePosition, true);
                window.removeEventListener('resize', updatePosition);
            };
        }
    }, [isOpen]);

    const handleSelect = (item) => {
        onChange(item[valueKey]);
        setIsOpen(false);
        setSearchTerm('');
    };

    const clearSelection = (e) => {
        e.stopPropagation();
        onChange(null);
    };

    return (
        <div className="relative w-full min-w-0" ref={wrapperRef}>
            <div
                ref={triggerRef}
                onClick={() => !disabled && setIsOpen(!isOpen)}
                className={`
                    w-full min-h-11 bg-gray-950 border rounded px-2 py-2 text-sm text-white flex items-center justify-between cursor-pointer transition-colors
                    ${disabled ? 'opacity-50 cursor-not-allowed border-gray-800' : 'border-gray-700 hover:border-gray-500 focus-within:border-indigo-500'}
                `}
            >
                {isOpen ? (
                    <input
                        autoFocus
                        type="text"
                        className="bg-transparent outline-none w-full text-white placeholder-gray-500"
                        placeholder="Cerca..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                    />
                ) : (
                    <span className={`truncate ${!selectedItem ? 'text-gray-500 italic' : ''}`}>
                        {selectedItem ? selectedItem[labelKey] : placeholder}
                    </span>
                )}

                <div className="flex items-center gap-1 shrink-0 ml-2">
                    {selectedItem && !disabled && !isOpen && (
                        <button type="button" onClick={clearSelection} className="text-gray-500 hover:text-red-400 p-0.5">
                            <X size={14} />
                        </button>
                    )}
                    <ChevronDown size={14} className={`text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                </div>
            </div>

            {isOpen &&
                createPortal(
                    <div
                        id={`dropdown-${uniqueId}`}
                        className={`fixed ${SEARCHABLE_DROPDOWN_Z_CLASS} bg-gray-900 border border-gray-700 rounded shadow-xl overflow-y-auto custom-scrollbar`}
                        style={{
                            top: dropdownPosition.top != null ? `${dropdownPosition.top}px` : undefined,
                            bottom: dropdownPosition.bottom != null ? `${dropdownPosition.bottom}px` : undefined,
                            left: `${dropdownPosition.left}px`,
                            width: `${dropdownPosition.width}px`,
                            maxHeight: dropdownPosition.maxHeight
                                ? `${dropdownPosition.maxHeight}px`
                                : '15rem',
                            zIndex: dropdownZIndex,
                        }}
                    >
                        {filteredOptions.length > 0 ? (
                            filteredOptions.map((opt) => {
                                const isSelected = String(opt[valueKey]) === String(value);
                                return (
                                    <button
                                        type="button"
                                        key={opt[valueKey]}
                                        onClick={() => handleSelect(opt)}
                                        className={`
                                        w-full min-h-11 px-3 py-2.5 text-sm text-left cursor-pointer flex justify-between items-center border-b border-gray-800 last:border-0 touch-manipulation
                                        ${isSelected ? 'bg-indigo-900/40 text-indigo-200 font-bold' : 'text-gray-300 hover:bg-gray-800 hover:text-white'}
                                    `}
                                    >
                                        <span className="min-w-0 break-words">{opt[labelKey]}</span>
                                        {isSelected && <Check size={14} className="text-indigo-400 shrink-0 ml-2" />}
                                    </button>
                                );
                            })
                        ) : (
                            <div className="p-3 text-center text-gray-500 text-xs italic">Nessun risultato.</div>
                        )}
                    </div>,
                    document.body
                )}
        </div>
    );
});

SearchableDropdown.displayName = 'SearchableDropdown';

const SearchableSelect = memo(
    ({
        options = [],
        value,
        onChange,
        placeholder = 'Seleziona...',
        labelKey = 'nome',
        valueKey = 'id',
        disabled = false,
        minOptionsForSearch = DEFAULT_MIN_OPTIONS_FOR_SEARCH,
        dropdownZIndex = 110,
        className = '',
    }) => {
        const useNative = options.length <= minOptionsForSearch;

        if (useNative) {
            return (
                <NativeSelect
                    options={options}
                    value={value}
                    onChange={onChange}
                    placeholder={placeholder}
                    labelKey={labelKey}
                    valueKey={valueKey}
                    disabled={disabled}
                    className={className}
                />
            );
        }

        return (
            <SearchableDropdown
                options={options}
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                labelKey={labelKey}
                valueKey={valueKey}
                disabled={disabled}
                dropdownZIndex={dropdownZIndex}
            />
        );
    }
);

SearchableSelect.displayName = 'SearchableSelect';

export default SearchableSelect;
