import { useMemo, useState } from "react";
import MseFieldTable from "./MseFieldTable";
import {
  amountFromText,
  amountToText,
  emptyPackItem,
  emptyPackType,
  emptyPackTypeItemRef,
  filterFromText,
  filterToText,
} from "../mse/packSpecUtils";

const PACK_TYPE_SELECT = ["all", "no replace", "replace", "first"];
const PACK_ITEM_SELECT = ["no replace", "replace", "first"];

function patchList(list, index, patch) {
  return list.map((row, i) => (i === index ? { ...row, ...patch } : row));
}

function PackItemsTable({ items, onChange, onStatusChange }) {
  if (!items.length) {
    return (
      <p className="mse-empty-hint">
        No pack items. Add reusable pools (e.g. common, rare) from the game file.
      </p>
    );
  }

  return (
    <table className="mse-field-table mse-pack-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Select</th>
          <th>Filter</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {items.map((item, idx) => (
          <tr key={`pi-${idx}`} onMouseEnter={() => onStatusChange?.(`Pack item: ${item.name || "(unnamed)"}`)}>
            <td>
              <input
                className="mse-field-input"
                value={item.name || ""}
                onChange={(e) => onChange(patchList(items, idx, { name: e.target.value }))}
              />
            </td>
            <td>
              <select
                className="mse-field-input"
                value={item.select || "no replace"}
                onChange={(e) => onChange(patchList(items, idx, { select: e.target.value }))}
              >
                {PACK_ITEM_SELECT.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </td>
            <td>
              <input
                className="mse-field-input"
                value={filterToText(item.filter)}
                placeholder='card.rarity == "COM"'
                onChange={(e) => onChange(patchList(items, idx, { filter: filterFromText(e.target.value) }))}
              />
            </td>
            <td>
              <button type="button" className="mse-btn-small btn-danger" onClick={() => onChange(items.filter((_, i) => i !== idx))}>
                ×
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function MseRandomPackTab({
  selectedGameId,
  draft,
  onChange,
  onSave,
  saving,
  dirty,
  selectablePacks,
  allPackTypes,
  selectedPackName,
  onSelectPackName,
  packCopies,
  onPackCopies,
  poolExpansionId,
  onPoolExpansion,
  espansioni,
  packCardPool,
  packSummaryRows,
  onGenerate,
  generatedPackResult,
  onOpenCard,
}) {
  const [statusText, setStatusText] = useState("");
  const packItems = draft?.pack_items || [];
  const packTypes = draft?.pack_types || [];

  const selectedType = useMemo(
    () => packTypes.find((p) => p.name === selectedPackName) || selectablePacks[0] || null,
    [packTypes, selectedPackName, selectablePacks]
  );

  const selectedTypeIndex = packTypes.findIndex((p) => p.name === selectedType?.name);

  const setItems = (next) => onChange({ ...draft, pack_items: next });
  const setTypes = (next) => onChange({ ...draft, pack_types: next });

  const patchSelectedType = (patch) => {
    if (selectedTypeIndex < 0) return;
    setTypes(patchList(packTypes, selectedTypeIndex, patch));
  };

  const typeFields = selectedType
    ? [
        { name: "name", type: "text", description: "Pack type name shown in the random pack panel." },
        {
          name: "select",
          type: "choice",
          choices: PACK_TYPE_SELECT.map((n) => ({ name: n })),
          description: "How items are combined when generating this pack.",
        },
        {
          name: "selectable",
          type: "boolean",
          description: "If yes, this pack type appears in the generator dropdown.",
        },
        {
          name: "summary",
          type: "boolean",
          description: "If yes, include this pack in the summary table.",
        },
        {
          name: "enabled",
          type: "boolean",
          description: "If no, this pack type is disabled.",
        },
      ]
    : [];

  const getTypeField = (field) => {
    if (!selectedType) return "";
    const k = field.name;
    if (k === "selectable" || k === "summary" || k === "enabled") {
      return selectedType[k] !== false ? "yes" : "no";
    }
    return selectedType[k] ?? "";
  };

  const setTypeField = (field, raw) => {
    const k = field.name;
    if (k === "selectable" || k === "summary" || k === "enabled") {
      patchSelectedType({ [k]: raw === "yes" || raw === true });
      return;
    }
    patchSelectedType({ [k]: raw });
  };

  if (!selectedGameId) {
    return (
      <section className="mse-pack-tab">
        <p className="mse-empty-hint">Select a game on the Cards tab to configure random packs.</p>
      </section>
    );
  }

  return (
    <section className="mse-pack-tab">
      <aside className="mse-pane mse-pane-list">
        <div className="mse-pane-title-row">
          <h2 className="mse-pane-title">Pack types</h2>
          <button type="button" className="mse-btn-small" onClick={() => setTypes([...packTypes, emptyPackType()])}>
            +
          </button>
        </div>
        <div className="mse-card-list-scroll">
          <table className="mse-card-list-table">
            <tbody>
              {packTypes.map((p) => (
                <tr
                  key={p.name || Math.random()}
                  className={p.name === selectedPackName ? "selected" : ""}
                  onClick={() => p.name && onSelectPackName(p.name)}
                >
                  <td>{p.name || "(unnamed)"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mse-pack-toolbar">
          <button type="button" onClick={onSave} disabled={saving || !dirty}>
            {saving ? "Saving…" : "Save game pack spec"}
          </button>
        </div>
      </aside>

      <div className="mse-pane mse-pane-fields">
        <div className="mse-pane-title-row">
          <h2 className="mse-pane-title">Pack items</h2>
          <button type="button" className="mse-btn-small" onClick={() => setItems([...packItems, emptyPackItem()])}>
            +
          </button>
        </div>
        <PackItemsTable items={packItems} onChange={setItems} onStatusChange={setStatusText} />

        <h2 className="mse-pane-title mse-sub-title">Selected pack type</h2>
        {selectedType ? (
          <>
            <MseFieldTable
              fields={typeFields}
              getValue={getTypeField}
              setValue={setTypeField}
              onStatusChange={setStatusText}
            />
            <div className="mse-pane-title-row">
              <strong>Items in pack</strong>
              <button
                type="button"
                className="mse-btn-small"
                onClick={() =>
                  patchSelectedType({ items: [...(selectedType.items || []), emptyPackTypeItemRef()] })
                }
              >
                +
              </button>
            </div>
            <table className="mse-field-table mse-pack-table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Amount</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {(selectedType.items || []).map((ref, rIdx) => (
                  <tr key={`ref-${rIdx}`}>
                    <td>
                      <select
                        className="mse-field-input"
                        value={ref.name || ""}
                        onChange={(e) => {
                          const items = [...(selectedType.items || [])];
                          items[rIdx] = { ...items[rIdx], name: e.target.value };
                          patchSelectedType({ items });
                        }}
                      >
                        <option value="">—</option>
                        {packItems.map((pi) => (
                          <option key={pi.name} value={pi.name}>
                            {pi.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        className="mse-field-input"
                        value={amountToText(ref.amount)}
                        onChange={(e) => {
                          const items = [...(selectedType.items || [])];
                          items[rIdx] = { ...items[rIdx], amount: amountFromText(e.target.value) };
                          patchSelectedType({ items });
                        }}
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="mse-btn-small btn-danger"
                        onClick={() =>
                          patchSelectedType({
                            items: (selectedType.items || []).filter((_, i) => i !== rIdx),
                          })
                        }
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : (
          <p className="mse-empty-hint">Select or add a pack type.</p>
        )}
      </div>

      <aside className="mse-pane mse-pane-preview">
        <h2 className="mse-pane-title">Random booster</h2>
        <div className="mse-pack-gen">
          <label>
            <span>Pack type</span>
            <select value={selectedPackName} onChange={(e) => onSelectPackName(e.target.value)}>
              {selectablePacks.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Copies</span>
            <input
              type="number"
              min={1}
              max={100}
              className="mse-field-input"
              value={packCopies}
              onChange={(e) => onPackCopies(Math.max(1, Number(e.target.value) || 1))}
            />
          </label>
          <label>
            <span>Card pool</span>
            <select value={poolExpansionId} onChange={(e) => onPoolExpansion(e.target.value)}>
              <option value="">All cards (game)</option>
              {espansioni
                .filter((e) => !selectedGameId || e.gioco_definizione === selectedGameId)
                .map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.nome}
                  </option>
                ))}
            </select>
          </label>
          <button type="button" onClick={onGenerate}>
            Generate
          </button>
        </div>
        <p className="mse-preview-meta">
          Pool: {packCardPool.length} cards · {selectablePacks.length}/{allPackTypes.length} selectable pack types
        </p>
        <table className="stats-table">
          <thead>
            <tr>
              <th>Pack type</th>
              <th>Cards (est.)</th>
            </tr>
          </thead>
          <tbody>
            {packSummaryRows.map((row) => (
              <tr key={row.name}>
                <td>{row.name}</td>
                <td>{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h3 className="mse-sub-title">Generated</h3>
        {!generatedPackResult ? (
          <p className="mse-empty-hint">Click Generate to simulate packs.</p>
        ) : (
          generatedPackResult.packs.map((pack, idx) => (
            <div key={`pack-${idx}`} className="pack-instance">
              <h4>Pack #{idx + 1}</h4>
              <ul className="mse-pack-card-list">
                {pack.map((card) => (
                  <li key={`${idx}-${card.id}`}>
                    <button type="button" onClick={() => onOpenCard(card)}>
                      {card.nome} ({card.codice}){card._pack_from ? ` · ${card._pack_from}` : ""}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))
        )}
      </aside>

      <footer className="mse-statusbar">{statusText || "Pack types compose pack items; filters use MSE script syntax on card fields."}</footer>
    </section>
  );
}
