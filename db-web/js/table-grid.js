// db-web/js/table-grid.js — Spreadsheet editable para una tabla

const TableGrid = (() => {
  const state = {
    table: null,
    columns: [],           // [{name, type, nullable, default, is_pk, fk_ref}]
    rows: [],
    total: 0,
    limit: 50,
    offset: 0,
    orderBy: null,
    orderDir: "desc",
    search: "",
    selectedIds: new Set(),
    editing: null,         // {rowIdx, colName}
  };

  function getPkCol() {
    const pk = state.columns.find(c => c.is_pk);
    return pk ? pk.name : "id";
  }

  async function load(table) {
    state.table = table;
    state.offset = 0;
    state.selectedIds.clear();
    state.orderBy = null;
    state.search = "";
    state.editing = null;
    try {
      state.columns = await window.api.columns(table);
      await fetchRows();
    } catch (err) {
      showToast(err.message || "Error al cargar tabla", "danger");
      render();
    }
  }

  async function fetchRows() {
    try {
      const params = { limit: state.limit, offset: state.offset };
      if (state.orderBy) { params.order_by = state.orderBy; params.order_dir = state.orderDir; }
      if (state.search)  { params.search = state.search; }
      const page = await window.api.rows(state.table, params);
      state.rows = page.rows;
      state.total = page.total;
      render();
    } catch (err) {
      showToast(err.message || "Error al cargar filas", "danger");
    }
  }

  function render() {
    const root = document.getElementById("data-pane");
    if (!state.table) {
      root.innerHTML = `<div style="padding:2rem; text-align:center; color:var(--text-muted);">Selecciona una tabla en el sidebar.</div>`;
      return;
    }
    const pkCol = getPkCol();
    const searchVal = escapeHtml(state.search);

    const headers = state.columns.map(c => {
      const arrow = state.orderBy === c.name ? (state.orderDir === "asc" ? " ↑" : " ↓") : "";
      const pkClass = c.is_pk ? "col-pk" : "";
      return `
        <th data-col="${escapeHtml(c.name)}">
          <span class="${pkClass}">${escapeHtml(c.name)}${arrow}</span>
          <span class="col-meta">${escapeHtml(c.type)}${c.is_pk ? " PK" : ""}${c.fk_ref ? " → " + escapeHtml(c.fk_ref) : ""}</span>
        </th>`;
    }).join("");

    const rowsHtml = state.rows.map((row, rIdx) => {
      const rowId = row[pkCol];
      const isSelected = state.selectedIds.has(String(rowId));
      const cells = state.columns.map(c => {
        const value = row[c.name];
        const isEditing = state.editing && state.editing.rowIdx === rIdx && state.editing.colName === c.name;
        const isPk = c.is_pk;
        if (isEditing) {
          const raw = value == null ? "" : String(value);
          return `<td class="editing"><input type="text" value="${escapeHtml(raw)}" data-row="${rIdx}" data-col="${escapeHtml(c.name)}" autofocus></td>`;
        }
        const nullClass = value == null ? "null" : "";
        const pkClass = isPk ? "pk" : "";
        return `<td class="${nullClass} ${pkClass}" data-row="${rIdx}" data-col="${escapeHtml(c.name)}" title="${escapeHtml(value == null ? "" : String(value))}">${formatCellValue(value)}</td>`;
      }).join("");
      return `
        <tr class="${isSelected ? 'selected' : ''}" data-row-id="${escapeHtml(String(rowId))}">
          <td class="checkbox-cell"><input type="checkbox" ${isSelected ? "checked" : ""} data-checkbox="${escapeHtml(String(rowId))}"></td>
          ${cells}
        </tr>`;
    }).join("");

    const canPrev = state.offset > 0;
    const canNext = state.offset + state.limit < state.total;
    const page = Math.floor(state.offset / state.limit) + 1;
    const pages = Math.max(1, Math.ceil(state.total / state.limit));

    root.innerHTML = `
      <div class="data-toolbar">
        <input class="input search" placeholder="🔍 Buscar en columnas de texto..." value="${searchVal}" id="grid-search">
        <button class="btn" id="btn-refresh">🔄 Refrescar</button>
        <button class="btn primary" id="btn-new">➕ Nueva fila</button>
        <button class="btn danger" id="btn-delete-selected" ${state.selectedIds.size === 0 ? "disabled" : ""}>🗑 Eliminar (${state.selectedIds.size})</button>
        <button class="btn" id="btn-export">📥 Export CSV</button>
      </div>
      <div class="grid-wrap">
        <table class="grid">
          <thead>
            <tr>
              <th class="checkbox-cell"><input type="checkbox" id="check-all"></th>
              ${headers}
            </tr>
          </thead>
          <tbody>${rowsHtml || `<tr><td colspan="${state.columns.length + 1}" style="text-align:center; padding:1.5rem; color:var(--text-muted);">Sin filas.</td></tr>`}</tbody>
        </table>
      </div>
      <div class="pagination">
        <div>${state.total.toLocaleString()} filas — pagina ${page} de ${pages}</div>
        <div class="controls">
          <button class="btn btn-sm" id="btn-prev" ${canPrev ? "" : "disabled"}>← Prev</button>
          <button class="btn btn-sm" id="btn-next" ${canNext ? "" : "disabled"}>Next →</button>
          <select class="select" style="width:auto;" id="sel-limit">
            ${[25, 50, 100, 200].map(v => `<option value="${v}" ${v === state.limit ? "selected" : ""}>${v} / pag</option>`).join("")}
          </select>
        </div>
      </div>
    `;
    bind();
  }

  function bind() {
    const root = document.getElementById("data-pane");
    root.querySelector("#btn-refresh")?.addEventListener("click", fetchRows);
    root.querySelector("#btn-new")?.addEventListener("click", openNewRowModal);
    root.querySelector("#btn-export")?.addEventListener("click", exportCsv);
    root.querySelector("#btn-delete-selected")?.addEventListener("click", deleteSelected);
    root.querySelector("#btn-prev")?.addEventListener("click", () => {
      if (state.offset > 0) { state.offset = Math.max(0, state.offset - state.limit); fetchRows(); }
    });
    root.querySelector("#btn-next")?.addEventListener("click", () => {
      if (state.offset + state.limit < state.total) { state.offset += state.limit; fetchRows(); }
    });
    root.querySelector("#sel-limit")?.addEventListener("change", (e) => {
      state.limit = Number(e.target.value); state.offset = 0; fetchRows();
    });
    const searchInput = root.querySelector("#grid-search");
    if (searchInput) {
      searchInput.addEventListener("input", debounce(() => {
        state.search = searchInput.value.trim();
        state.offset = 0;
        fetchRows();
      }, 350));
    }

    // Orden por click en headers
    root.querySelectorAll("th[data-col]").forEach(th => {
      th.addEventListener("click", () => {
        const col = th.dataset.col;
        if (state.orderBy === col) {
          state.orderDir = state.orderDir === "asc" ? "desc" : "asc";
        } else {
          state.orderBy = col; state.orderDir = "asc";
        }
        fetchRows();
      });
    });

    // Checkboxes
    const checkAll = root.querySelector("#check-all");
    if (checkAll) {
      checkAll.addEventListener("change", () => {
        const pk = getPkCol();
        if (checkAll.checked) state.rows.forEach(r => state.selectedIds.add(String(r[pk])));
        else state.selectedIds.clear();
        render();
      });
    }
    root.querySelectorAll("input[data-checkbox]").forEach(cb => {
      cb.addEventListener("change", (e) => {
        const id = cb.dataset.checkbox;
        if (cb.checked) state.selectedIds.add(id); else state.selectedIds.delete(id);
        render();
      });
    });

    // Doble click en celdas = editar
    root.querySelectorAll("td[data-row][data-col]").forEach(td => {
      td.addEventListener("dblclick", () => {
        const rIdx = Number(td.dataset.row);
        const col = td.dataset.col;
        const colInfo = state.columns.find(c => c.name === col);
        if (colInfo?.is_pk) { showToast("No se puede editar la PK inline. Usa SQL.", "warning"); return; }
        state.editing = { rowIdx: rIdx, colName: col };
        render();
      });
    });

    // Enter / Esc en input de edicion
    const editingInput = root.querySelector("td.editing input");
    if (editingInput) {
      editingInput.focus();
      editingInput.select();
      editingInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); saveEdit(editingInput); }
        else if (e.key === "Escape") { state.editing = null; render(); }
      });
      editingInput.addEventListener("blur", () => saveEdit(editingInput));
    }
  }

  async function saveEdit(inputEl) {
    const rIdx = Number(inputEl.dataset.row);
    const col = inputEl.dataset.col;
    const row = state.rows[rIdx];
    if (!row) { state.editing = null; render(); return; }
    const colInfo = state.columns.find(c => c.name === col);
    const newValueRaw = inputEl.value;
    const newValue = parseCellInput(newValueRaw, colInfo?.type);
    const currentValue = row[col];
    if (String(newValue) === String(currentValue)) {
      state.editing = null; render(); return;
    }
    const pk = getPkCol();
    const pkValue = row[pk];
    try {
      const updated = await window.api.updateRow(state.table, pkValue, { [col]: newValue });
      state.rows[rIdx] = updated;
      showToast("Fila actualizada", "success");
    } catch (err) {
      showToast(err.message || "Error al actualizar", "danger");
    }
    state.editing = null;
    render();
  }

  async function openNewRowModal() {
    // Construir form con inputs para cada columna no-PK-autogenerada
    const editableCols = state.columns.filter(c => {
      // saltar columnas con default server-side (uuid, serial, timestamp con now)
      if (c.is_pk && (c.default || "").includes("gen_random_uuid")) return false;
      if ((c.default || "").includes("now()") || (c.default || "").includes("CURRENT_TIMESTAMP")) return false;
      return true;
    });
    const modal = document.createElement("div");
    modal.style.cssText = "position:fixed; inset:0; background:rgba(0,0,0,.6); display:flex; align-items:center; justify-content:center; z-index:300;";
    const fields = editableCols.map(c => `
      <div class="form-group">
        <label><strong>${escapeHtml(c.name)}</strong> <span style="color:var(--text-dim); font-family:var(--mono); font-size:.72rem;">${escapeHtml(c.type)}${c.nullable ? "" : " NOT NULL"}${c.default ? " DEFAULT " + escapeHtml(c.default.slice(0, 30)) : ""}</span></label>
        <input class="input" name="${escapeHtml(c.name)}" placeholder="${c.nullable ? "(NULL si vacio)" : ""}">
      </div>`).join("");
    modal.innerHTML = `
      <div style="background:var(--surface); padding:1.5rem; border-radius:8px; width:100%; max-width:540px; max-height:85vh; overflow-y:auto; border:1px solid var(--border);">
        <h3 style="margin:0 0 1rem;">Nueva fila en <code style="color:var(--accent);">${escapeHtml(state.table)}</code></h3>
        <form id="new-row-form">${fields}</form>
        <div style="display:flex; gap:.5rem; justify-content:flex-end; margin-top:1rem;">
          <button class="btn" id="cancel-new">Cancelar</button>
          <button class="btn primary" id="save-new">Guardar</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
    const close = () => modal.remove();
    modal.querySelector("#cancel-new").onclick = close;
    modal.addEventListener("click", (e) => { if (e.target === modal) close(); });
    modal.querySelector("#save-new").onclick = async () => {
      const form = modal.querySelector("#new-row-form");
      const body = {};
      form.querySelectorAll("input[name]").forEach(el => {
        const col = state.columns.find(c => c.name === el.name);
        const parsed = parseCellInput(el.value, col?.type);
        if (parsed !== null && parsed !== "") body[el.name] = parsed;
      });
      try {
        await window.api.insertRow(state.table, body);
        showToast("Fila insertada", "success");
        close();
        await fetchRows();
      } catch (err) {
        showToast(err.message || "Error al insertar", "danger");
      }
    };
  }

  async function deleteSelected() {
    if (!state.selectedIds.size) return;
    if (!confirmDialog(`¿Eliminar ${state.selectedIds.size} fila(s) de ${state.table}? Esta accion no se puede deshacer.`)) return;
    let deleted = 0, failed = 0;
    for (const pk of state.selectedIds) {
      try { await window.api.deleteRow(state.table, pk); deleted++; }
      catch (err) { failed++; console.error("[delete]", pk, err); }
    }
    showToast(`${deleted} eliminada(s)${failed ? `, ${failed} error(es)` : ""}`, failed ? "warning" : "success");
    state.selectedIds.clear();
    await fetchRows();
  }

  async function exportCsv() {
    try {
      const resp = await fetch(window.api.exportUrl(state.table), {
        headers: { "Authorization": `Bearer ${window.apiAuth.getToken()}` },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${state.table}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast("CSV descargado", "success");
    } catch (err) {
      showToast(err.message || "Error al exportar", "danger");
    }
  }

  return { load, render };
})();
