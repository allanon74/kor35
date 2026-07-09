import {
  amountFromText,
  amountToText,
  emptyPackItem,
  emptyPackType,
  emptyPackTypeItemRef,
  filterFromText,
  filterToText,
} from "../mse/packSpecUtils";

const SELECT_MODES = ["all", "no replace", "replace", "first"];
const ITEM_SELECT_MODES = ["no replace", "replace", "first"];

function patchList(list, index, patch) {
  return list.map((row, i) => (i === index ? { ...row, ...patch } : row));
}

export default function PackSpecEditor({
  draft,
  onChange,
  onSave,
  saving,
  dirty,
}) {
  const packItems = draft?.pack_items || [];
  const packTypes = draft?.pack_types || [];

  const setItems = (next) => onChange({ ...draft, pack_items: next });
  const setTypes = (next) => onChange({ ...draft, pack_types: next });

  return (
    <section className="pack-spec-editor">
      <div className="pack-editor-head">
        <h3>Pack definition</h3>
        <button type="button" onClick={onSave} disabled={saving || !dirty}>
          {saving ? "Saving…" : "Save pack spec"}
        </button>
      </div>
      <p className="hint">
        Pack item = pool filtrato riusabile. Pack type = composizione di item (come in MSE game file).
      </p>

      <article className="pack-editor-block">
        <div className="pack-editor-block-head">
          <h4>Pack items</h4>
          <button
            type="button"
            onClick={() => setItems([...packItems, emptyPackItem()])}
          >
            + Item
          </button>
        </div>
        {!packItems.length ? (
          <p className="hint">Nessun pack item. Aggiungine uno per definire pool (es. common, rare).</p>
        ) : (
          packItems.map((item, idx) => (
            <div className="pack-editor-row" key={`pi-${idx}`}>
              <label className="field inline">
                <span>Name</span>
                <input
                  value={item.name || ""}
                  onChange={(e) => setItems(patchList(packItems, idx, { name: e.target.value }))}
                />
              </label>
              <label className="field inline">
                <span>Select</span>
                <select
                  value={item.select || "no replace"}
                  onChange={(e) => setItems(patchList(packItems, idx, { select: e.target.value }))}
                >
                  {ITEM_SELECT_MODES.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field pack-filter-field">
                <span>Filter (script)</span>
                <input
                  value={filterToText(item.filter)}
                  placeholder='card.rarity == "COM"'
                  onChange={(e) =>
                    setItems(patchList(packItems, idx, { filter: filterFromText(e.target.value) }))
                  }
                />
              </label>
              <button
                type="button"
                className="btn-danger"
                onClick={() => setItems(packItems.filter((_, i) => i !== idx))}
              >
                Remove
              </button>
            </div>
          ))
        )}
      </article>

      <article className="pack-editor-block">
        <div className="pack-editor-block-head">
          <h4>Pack types</h4>
          <button
            type="button"
            onClick={() => setTypes([...packTypes, emptyPackType()])}
          >
            + Pack type
          </button>
        </div>
        {!packTypes.length ? (
          <p className="hint">Nessun pack type. Aggiungine uno (es. booster) con riferimenti agli item.</p>
        ) : (
          packTypes.map((pack, pIdx) => {
            const refs = pack.items || [];
            const patchPack = (patch) =>
              setTypes(patchList(packTypes, pIdx, patch));
            const setRefs = (next) => patchPack({ items: next });

            return (
              <div className="pack-type-card" key={`pt-${pIdx}`}>
                <div className="pack-editor-row">
                  <label className="field inline">
                    <span>Name</span>
                    <input
                      value={pack.name || ""}
                      onChange={(e) => patchPack({ name: e.target.value })}
                    />
                  </label>
                  <label className="field inline">
                    <span>Select</span>
                    <select
                      value={pack.select || "all"}
                      onChange={(e) => patchPack({ select: e.target.value })}
                    >
                      {SELECT_MODES.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field inline field-checkbox">
                    <input
                      type="checkbox"
                      checked={pack.selectable !== false}
                      onChange={(e) => patchPack({ selectable: e.target.checked })}
                    />
                    <span>Selectable</span>
                  </label>
                  <label className="field inline field-checkbox">
                    <input
                      type="checkbox"
                      checked={pack.summary !== false}
                      onChange={(e) => patchPack({ summary: e.target.checked })}
                    />
                    <span>Summary</span>
                  </label>
                  <label className="field inline field-checkbox">
                    <input
                      type="checkbox"
                      checked={pack.enabled !== false}
                      onChange={(e) => patchPack({ enabled: e.target.checked })}
                    />
                    <span>Enabled</span>
                  </label>
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={() => setTypes(packTypes.filter((_, i) => i !== pIdx))}
                  >
                    Remove pack
                  </button>
                </div>

                <div className="pack-type-items">
                  <div className="pack-editor-block-head">
                    <strong>Items in pack</strong>
                    <button
                      type="button"
                      onClick={() => setRefs([...refs, emptyPackTypeItemRef()])}
                    >
                      + Ref
                    </button>
                  </div>
                  {!refs.length ? (
                    <p className="hint">Aggiungi riferimenti a pack item (name + amount).</p>
                  ) : (
                    refs.map((ref, rIdx) => (
                      <div className="pack-editor-row pack-ref-row" key={`ref-${pIdx}-${rIdx}`}>
                        <label className="field inline">
                          <span>Item name</span>
                          <input
                            list={`pack-item-names-${pIdx}`}
                            value={ref.name || ""}
                            onChange={(e) =>
                              setRefs(patchList(refs, rIdx, { name: e.target.value }))
                            }
                          />
                        </label>
                        <datalist id={`pack-item-names-${pIdx}`}>
                          {packItems.map((pi) => (
                            <option key={pi.name} value={pi.name} />
                          ))}
                        </datalist>
                        <label className="field inline">
                          <span>Amount</span>
                          <input
                            value={amountToText(ref.amount)}
                            onChange={(e) =>
                              setRefs(
                                patchList(refs, rIdx, { amount: amountFromText(e.target.value) })
                              )
                            }
                          />
                        </label>
                        <button
                          type="button"
                          className="btn-danger"
                          onClick={() => setRefs(refs.filter((_, i) => i !== rIdx))}
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })
        )}
      </article>
    </section>
  );
}
