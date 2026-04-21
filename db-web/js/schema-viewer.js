// db-web/js/schema-viewer.js — render metadata de columnas de una tabla

const SchemaViewer = (() => {
  let currentTable = null;

  async function load(table) {
    currentTable = table;
    const root = document.getElementById("schema-pane");
    if (!table) {
      root.innerHTML = `<div style="padding:2rem; text-align:center; color:var(--text-muted);">Selecciona una tabla.</div>`;
      return;
    }
    root.innerHTML = `<div style="padding:1rem; color:var(--text-muted);">Cargando schema...</div>`;
    try {
      const columns = await window.api.columns(table);
      render(table, columns);
    } catch (err) {
      root.innerHTML = `<div style="padding:1rem; color:var(--danger);">Error: ${escapeHtml(err.message || "")}</div>`;
    }
  }

  function render(table, cols) {
    const root = document.getElementById("schema-pane");
    const rows = cols.map(c => `
      <tr>
        <td><strong>${escapeHtml(c.name)}</strong></td>
        <td><code>${escapeHtml(c.type)}</code></td>
        <td class="${c.nullable ? 'null-yes' : 'null-no'}">${c.nullable ? "YES" : "NO"}</td>
        <td>${c.default ? `<code>${escapeHtml(c.default)}</code>` : "<span class=\"null-yes\">—</span>"}</td>
        <td>${c.is_pk ? '<span class="pk-badge">PK</span>' : ""}</td>
        <td>${c.fk_ref ? `<span class="fk-badge">FK</span> <code>${escapeHtml(c.fk_ref)}</code>` : ""}</td>
      </tr>`).join("");

    root.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h3 style="margin:0; font-family:var(--mono); color:var(--accent); font-size:1rem;">${escapeHtml(table)}</h3>
        <p style="color:var(--text-muted); margin:.25rem 0 0; font-size:.8rem;">${cols.length} columnas</p>
      </div>
      <div class="schema-grid">
        <table>
          <thead>
            <tr>
              <th>Columna</th>
              <th>Tipo</th>
              <th>Nullable</th>
              <th>Default</th>
              <th>PK</th>
              <th>FK</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  return { load };
})();
