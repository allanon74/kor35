import React, { useState, useEffect, useRef, useMemo, memo } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, X, Check } from 'lucide-react';
import { useDebounce } from '../../hooks/useDebounce';

/** Sotto questa soglia si usa un `<select>` nativo (liste corte, UX più immediata). */
export const DEFAULT_MIN_OPTIONS_FOR_SEARCH = 12;

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
            className={`w-full bg-gray-950 border border-gray-700 rounded px-2 py-1.5 text-sm text-white outline-none focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
            value={value === null || value === undefined ? '' : String(value)}
            disabled={disabled}
            onChange={(e) => {
                const v = e.target.value;
                if (v === '') {
                    onChange(null);
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
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 });
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
        const handleClickOutside = (event) => {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
                const dropdownElement = document.getElementById(`dropdown-${uniqueId}`);
                if (!dropdownElement || !dropdownElement.contains(event.target)) {
                    setIsOpen(false);
                }
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [uniqueId]);

    useEffect(() => {
        if (!isOpen) setSearchTerm('');
    }, [isOpen]);

    useEffect(() => {
        if (isOpen && triggerRef.current) {
            const updatePosition = () => {
                const rect = triggerRef.current.getBoundingClientRect();
                setDropdownPosition({
                    top: rect.bottom + window.scrollY + 4,
                    left: rect.left + window.scrollX,
                    width: rect.width,
                });
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
        <div className="relative w-full" ref={wrapperRef}>
            <div
                ref={triggerRef}
                onClick={() => !disabled && setIsOpen(!isOpen)}
                className={`
                    w-full bg-gray-950 border rounded px-2 py-1.5 text-sm text-white flex items-center justify-between cursor-pointer transition-colors
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
                        className="fixed z-50 bg-gray-900 border border-gray-700 rounded shadow-xl max-h-60 overflow-y-auto custom-scrollbar"
                        style={{
                            top: `${dropdownPosition.top}px`,
                            left: `${dropdownPosition.left}px`,
                            width: `${dropdownPosition.width}px`,
                        }}
                    >
                        {filteredOptions.length > 0 ? (
                            filteredOptions.map((opt) => {
                                const isSelected = String(opt[valueKey]) === String(value);
                                return (
                                    <div
                                        key={opt[valueKey]}
                                        onClick={() => handleSelect(opt)}
                                        className={`
                                        px-3 py-2 text-sm cursor-pointer flex justify-between items-center border-b border-gray-800 last:border-0
                                        ${isSelected ? 'bg-indigo-900/40 text-indigo-200 font-bold' : 'text-gray-300 hover:bg-gray-800 hover:text-white'}
                                    `}
                                    >
                                        <span>{opt[labelKey]}</span>
                                        {isSelected && <Check size={14} className="text-indigo-400" />}
                                    </div>
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
            />
        );
    }
);

SearchableSelect.displayName = 'SearchableSelect';

export default SearchableSelect;
