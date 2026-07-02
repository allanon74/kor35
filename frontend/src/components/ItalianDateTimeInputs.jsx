import React, { useEffect, useState } from 'react';
import {
  isoToItalianDate,
  italianDateToIso,
  isoToItalianDateTime,
  italianDateTimeToIso,
  isoToItalianTime,
  italianTimeToIso,
} from '../utils/italianDateTime';

function useItalianTextInput({ value, toDisplay, toIso, onChange }) {
  const [text, setText] = useState(() => toDisplay(value));
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!focused) {
      setText(toDisplay(value));
    }
  }, [value, focused, toDisplay]);

  const handleBlur = () => {
    setFocused(false);
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

  return {
    text,
    setText,
    setFocused,
    handleBlur,
  };
}

const inputDefaults = {
  type: 'text',
  lang: 'it-IT',
  autoComplete: 'off',
};

export function ItalianDateInput({ value, onChange, className = '', ...rest }) {
  const { text, setText, setFocused, handleBlur } = useItalianTextInput({
    value,
    toDisplay: isoToItalianDate,
    toIso: italianDateToIso,
    onChange,
  });

  return (
    <input
      {...inputDefaults}
      inputMode="numeric"
      placeholder="gg/mm/aaaa"
      className={className}
      value={text}
      onFocus={() => setFocused(true)}
      onChange={(e) => setText(e.target.value)}
      onBlur={handleBlur}
      {...rest}
    />
  );
}

export function ItalianDateTimeInput({ value, onChange, className = '', ...rest }) {
  const { text, setText, setFocused, handleBlur } = useItalianTextInput({
    value,
    toDisplay: isoToItalianDateTime,
    toIso: italianDateTimeToIso,
    onChange,
  });

  return (
    <input
      {...inputDefaults}
      inputMode="numeric"
      placeholder="gg/mm/aaaa, hh:mm"
      className={className}
      value={text}
      onFocus={() => setFocused(true)}
      onChange={(e) => setText(e.target.value)}
      onBlur={handleBlur}
      {...rest}
    />
  );
}

export function ItalianTimeInput({ value, onChange, className = '', ...rest }) {
  const { text, setText, setFocused, handleBlur } = useItalianTextInput({
    value,
    toDisplay: isoToItalianTime,
    toIso: italianTimeToIso,
    onChange,
  });

  return (
    <input
      {...inputDefaults}
      inputMode="numeric"
      placeholder="hh:mm"
      className={className}
      value={text}
      onFocus={() => setFocused(true)}
      onChange={(e) => setText(e.target.value)}
      onBlur={handleBlur}
      {...rest}
    />
  );
}
