import React, { useEffect, useRef, useState } from 'react';
import { Calendar, CalendarClock, Clock } from 'lucide-react';
import {
  isoToItalianDate,
  italianDateToIso,
  isoToItalianDateTime,
  italianDateTimeToIso,
  isoToItalianTime,
  italianTimeToIso,
  isoToNativeDateValue,
  isoToNativeDateTimeLocalValue,
  isoToNativeTimeValue,
} from '../utils/italianDateTime';

function useItalianTextInput({ value, toDisplay, toIso, onChange }) {
  const [text, setText] = useState(() => toDisplay(value));
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!focused) {
      setText(toDisplay(value));
    }
  }, [value, focused, toDisplay]);

  const commitText = () => {
    const iso = toIso(text);
    if (iso === null && text.trim()) {
      setText(toDisplay(value));
      return;
    }
    if (iso !== value) {
      onChange(iso);
    }
    setText(toDisplay(iso === null ? value : iso));
  };

  const handleBlur = () => {
    setFocused(false);
    commitText();
  };

  const applyPickerValue = (nativeValue) => {
    setFocused(false);
    onChange(nativeValue);
    setText(toDisplay(nativeValue));
  };

  return {
    text,
    setText,
    setFocused,
    handleBlur,
    applyPickerValue,
  };
}

function useNativePicker(pickerRef) {
  return () => {
    const el = pickerRef.current;
    if (!el) return;
    if (typeof el.showPicker === 'function') {
      try {
        el.showPicker();
        return;
      } catch {
        // showPicker può fallire se non c'è gesto utente
      }
    }
    el.focus();
    el.click();
  };
}

const inputDefaults = {
  type: 'text',
  lang: 'it-IT',
  autoComplete: 'off',
};

function ItalianPickerShell({
  className = '',
  textInput,
  pickerInput,
  pickerLabel,
  PickerIcon,
}) {
  const pickerRef = useRef(null);
  const openPicker = useNativePicker(pickerRef);

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {textInput}
      <button
        type="button"
        className="shrink-0 rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-700/60 hover:text-indigo-300"
        onClick={openPicker}
        aria-label={pickerLabel}
        title={pickerLabel}
      >
        <PickerIcon size={18} aria-hidden />
      </button>
      {pickerInput(pickerRef)}
    </div>
  );
}

export function ItalianDateInput({ value, onChange, className = '', ...rest }) {
  const { text, setText, setFocused, handleBlur, applyPickerValue } = useItalianTextInput({
    value,
    toDisplay: isoToItalianDate,
    toIso: italianDateToIso,
    onChange,
  });

  return (
    <ItalianPickerShell
      className={className}
      pickerLabel="Apri calendario"
      PickerIcon={Calendar}
      textInput={(
        <input
          {...inputDefaults}
          inputMode="numeric"
          placeholder="gg/mm/aaaa"
          className="min-w-0 flex-1 bg-transparent p-0 outline-none"
          value={text}
          onFocus={() => setFocused(true)}
          onChange={(e) => setText(e.target.value)}
          onBlur={handleBlur}
          {...rest}
        />
      )}
      pickerInput={(pickerRef) => (
        <input
          ref={pickerRef}
          type="date"
          lang="it-IT"
          tabIndex={-1}
          aria-hidden="true"
          className="sr-only"
          value={isoToNativeDateValue(value)}
          onChange={(e) => applyPickerValue(e.target.value)}
        />
      )}
    />
  );
}

export function ItalianDateTimeInput({ value, onChange, className = '', ...rest }) {
  const { text, setText, setFocused, handleBlur, applyPickerValue } = useItalianTextInput({
    value,
    toDisplay: isoToItalianDateTime,
    toIso: italianDateTimeToIso,
    onChange,
  });

  return (
    <ItalianPickerShell
      className={className}
      pickerLabel="Apri calendario data e ora"
      PickerIcon={CalendarClock}
      textInput={(
        <input
          {...inputDefaults}
          inputMode="numeric"
          placeholder="gg/mm/aaaa, hh:mm"
          className="min-w-0 flex-1 bg-transparent p-0 outline-none"
          value={text}
          onFocus={() => setFocused(true)}
          onChange={(e) => setText(e.target.value)}
          onBlur={handleBlur}
          {...rest}
        />
      )}
      pickerInput={(pickerRef) => (
        <input
          ref={pickerRef}
          type="datetime-local"
          lang="it-IT"
          tabIndex={-1}
          aria-hidden="true"
          className="sr-only"
          value={isoToNativeDateTimeLocalValue(value)}
          onChange={(e) => applyPickerValue(e.target.value)}
        />
      )}
    />
  );
}

export function ItalianTimeInput({ value, onChange, className = '', ...rest }) {
  const { text, setText, setFocused, handleBlur, applyPickerValue } = useItalianTextInput({
    value,
    toDisplay: isoToItalianTime,
    toIso: italianTimeToIso,
    onChange,
  });

  return (
    <ItalianPickerShell
      className={className}
      pickerLabel="Apri selettore orario"
      PickerIcon={Clock}
      textInput={(
        <input
          {...inputDefaults}
          inputMode="numeric"
          placeholder="hh:mm"
          className="min-w-0 flex-1 bg-transparent p-0 outline-none"
          value={text}
          onFocus={() => setFocused(true)}
          onChange={(e) => setText(e.target.value)}
          onBlur={handleBlur}
          {...rest}
        />
      )}
      pickerInput={(pickerRef) => (
        <input
          ref={pickerRef}
          type="time"
          lang="it-IT"
          tabIndex={-1}
          aria-hidden="true"
          className="sr-only"
          value={isoToNativeTimeValue(value)}
          onChange={(e) => applyPickerValue(e.target.value)}
        />
      )}
    />
  );
}
