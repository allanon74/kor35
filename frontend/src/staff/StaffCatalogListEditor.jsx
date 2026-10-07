import React, { memo, useEffect, useState } from 'react';
import { StaffToolShell } from './StaffToolShell';
import MasterGenericList from '../components/editors/MasterGenericList';
import StaffEditorModal from '../components/editors/StaffEditorModal';
import { isSiglaSistema } from './staffCatalogForm';

/**
 * Shell lista + modale per cataloghi staff (statistiche, aure, caratteristiche, …).
 */
const StaffCatalogListEditor = ({
  title,
  hint,
  persistKey,
  addLabel,
  emptyMessage,
  columns,
  emptyForm,
  loadItems,
  saveItem,
  deleteItem,
  FormPanel,
  formExtraProps,
  modalSize = 'lg',
  isSistema = isSiglaSistema,
  filterConfig = [],
  getSearchText = (item) => `${item?.sigla || ''} ${item?.nome || ''} ${item?.aura_nome || ''} ${item?.tipo || ''}`,
}) => {
  const [items, setItems] = useState([]);
  const [editingItem, setEditingItem] = useState(null);
  const [editorStatus, setEditorStatus] = useState({ type: 'success', message: '' });
  const [lookups, setLookups] = useState({});

  const refresh = async () => {
    const data = await loadItems();
    if (Array.isArray(data)) {
      setItems(data);
      return data;
    }
    setItems(data?.items || []);
    if (data?.lookups) setLookups(data.lookups);
    return data;
  };

  useEffect(() => {
    refresh().catch((err) => {
      console.error(err);
      setItems([]);
    });
  }, []);

  const saveEditor = async (form, mode = 'save_close') => {
    const saved = await saveItem(form, mode, setEditorStatus);
    if (saved === false) return;
    const recordName = saved?.nome || form.nome || 'Record';
    if (mode === 'save_as_new') {
      setEditorStatus({ type: 'success', message: `Nuovo record "${recordName}" inserito.` });
    }
    if (mode === 'save_continue') {
      setEditorStatus({ type: 'success', message: `"${recordName}" salvato.` });
    }
    if (mode === 'save_new_blank') {
      setEditorStatus({ type: 'success', message: `"${recordName}" salvato. Pronto per un nuovo inserimento.` });
    }
    if (mode === 'save_close') {
      setEditingItem(null);
      setEditorStatus({ type: 'success', message: '' });
    } else if (mode === 'save_new_blank') {
      setEditingItem({ ...emptyForm });
    } else if (saved?.id) {
      setEditingItem(saved);
    }
    await refresh();
  };

  return (
    <StaffToolShell className="space-y-4" fill>
      {hint ? <p className="text-sm text-gray-400 px-1 break-words">{hint}</p> : null}
      {editorStatus.message && !editingItem ? (
        <p className={`text-sm px-1 ${editorStatus.type === 'warning' ? 'text-amber-400' : 'text-red-400'}`}>
          {editorStatus.message}
        </p>
      ) : null}
      <MasterGenericList
        title={title}
        items={items}
        columns={columns}
        persistKey={persistKey}
        filterConfig={filterConfig}
        getSearchText={getSearchText}
        onAdd={() => setEditingItem({ ...emptyForm })}
        onEdit={(item) => setEditingItem({ ...emptyForm, ...item })}
        onDelete={async (id) => {
          const item = items.find((x) => x.id === id);
          if (isSistema(item)) {
            setEditorStatus({
              type: 'warning',
              message: `«${item.sigla || item.nome}» è un record di sistema e non si elimina da qui.`,
            });
            return;
          }
          await deleteItem(id);
          await refresh();
        }}
        addLabel={addLabel}
        emptyMessage={emptyMessage}
      />
      {editingItem && (
        <StaffEditorModal
          title={editingItem.id ? `Modifica ${title.toLowerCase()}` : `Nuovo: ${title}`}
          size={modalSize}
          showSave={false}
          onClose={() => {
            setEditingItem(null);
            setEditorStatus({ type: 'success', message: '' });
          }}
        >
          <FormPanel
            value={editingItem}
            items={items}
            lookups={lookups}
            {...(formExtraProps || {})}
            onClose={() => {
              setEditingItem(null);
              setEditorStatus({ type: 'success', message: '' });
            }}
            statusMessage={editorStatus.message}
            statusType={editorStatus.type}
            onSave={saveEditor}
          />
        </StaffEditorModal>
      )}
    </StaffToolShell>
  );
};

export default memo(StaffCatalogListEditor);
