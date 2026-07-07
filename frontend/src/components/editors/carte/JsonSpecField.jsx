import React, { useEffect, useMemo, useState } from 'react';
import { LabeledField, staffInputClass } from '../../../staff/StaffCrudUi';

function toPrettyJson(value) {
  if (value === null || value === undefined) return '{}';
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return '{}';
    try {
      return JSON.stringify(JSON.parse(trimmed), null, 2);
    } catch {
      return value;
    }
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return '{}';
  }
}

export function parseJsonObject(value, fieldName) {
  if (value === null || value === undefined || value === '') return {};
  if (typeof value === 'object' && !Array.isArray(value)) return value;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return {};
    const parsed = JSON.parse(trimmed);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      throw new Error(`${fieldName}: atteso oggetto JSON.`);
    }
    return parsed;
  }
  throw new Error(`${fieldName}: formato non valido.`);
}

export default function JsonSpecField({
  label,
  hint,
  value,
  onChange,
  minRows = 8,
  placeholder = '{}',
}) {
  const [text, setText] = useState(() => toPrettyJson(value));
  const [error, setError] = useState('');

  useEffect(() => {
    setText(toPrettyJson(value));
    setError('');
  }, [value]);

  const lineCount = useMemo(() => Math.max(minRows, text.split('\n').length), [text, minRows]);

  const commit = (raw) => {
    try {
      const obj = parseJsonObject(raw, label);
      onChange(obj);
      setText(JSON.stringify(obj, null, 2));
      setError('');
      return true;
    } catch (e) {
      setError(e?.message || 'JSON non valido.');
      return false;
    }
  };

  return (
    <LabeledField label={label} hint={hint}>
      <textarea
        className={`${staffInputClass('min-h-[120px] font-mono text-xs')} ${error ? 'border-red-600' : ''}`}
        rows={lineCount}
        spellCheck={false}
        placeholder={placeholder}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          if (error) setError('');
        }}
        onBlur={() => commit(text)}
      />
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </LabeledField>
  );
}

export function validateJsonFields(fields) {
  const errors = [];
  fields.forEach(({ name, value }) => {
    try {
      parseJsonObject(value, name);
    } catch (e) {
      errors.push(e.message);
    }
  });
  return errors;
}
