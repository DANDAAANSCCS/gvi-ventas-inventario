// db-web/js/sql-editor.js — Editor SQL + historial en localStorage

const SqlEditor = (() => {
  const HISTORY_KEY = "gv_dbmgr_sql_history";
  const MAX_HISTORY = 20;

  function getHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch { return []; }
  }
  function pushHistory(sql) {
    const trimmed = sql.trim();
    if (!trimmed) return;
    let hist = getHistory().filter(q => q !== trimmed);
    hist.unshift(trimmed);
    hist = hist.slice(0, MAX_HISTORY);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(hist));
  }

  function init() {
    const root = document.getElementById("sql-pane");
    root.innerHTML = `
      <div class="sql-editor">
        <div class="editor-bar">
          <button class="btn primary" id="sql-run">▶ Ejecutar <small style="opacity:.7; margin-left:.25rem;">(Ctrl+Enter)</small></button>
          <label class="checkbox-label">
            <input type="checkbox" id="sql-destructive">
            Permitir destructive (DROP / TRUNCATE / ALTER)
          </label>
          <button class="btn" id="sql-clear">Limpiar</button>
        </div>
        <textarea id="sql-input" placeholder="SELECT * FROM products LIMIT 10;" spellcheck="false"></textarea>
        <div class="history" id="sql-history"></div>
        <div class="sql-result" id="sql-result">
          <div class="meta">Ejecuta una consulta para ver los resultados aqui.</div>
        </div>
      </div>
    `;

    const input = document.getElementById("sql-input");
    const destr = document.getElementById("sql-destructive");
    const result = document.getElementById("sql-result");

    document.getElementById("sql-run").addEventListener("click", () => run(input.value, destr.checked));
    document.getElementById("sql-clear").addEventListener("click", () => { input.value = ""; input.focus(); });
    input.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); run(input.value, destr.checked); }
    });

    renderHistory();
  }

  function renderHistory() {
    const hist = getHistory();
    const box = document.getElementById("sql-history");
    if (!hist.length) { box.innerHTML = `<span style="font-size:.72rem;">Historial vacio.</span>`; return; }
    box.innerHTML = `<span style="font-size:.72rem; margin-right:.25rem;">Historial:</span>` +
      hist.map((q, i) => `<button data-idx="${i}" title="${escapeHtml(q)}">${escapeHtml(q.slice(0, 60))}${q.length > 60 ? "..." : ""}</button>`).join("");
    box.querySelectorAll("button[data-idx]").forEach(b => {
      b.addEventListener("click", () => {
        document.getElementById("sql-input").value = hist[Number(b.dataset.idx)];
        document.getElementById("sql-input").focus();
      });
    });
  }

  async function run(sql, allowDestructive) {
    const result = document.getElementById("sql-result");
    const trimmed = (sql || "").trim();
    if (!trimmed) { result.innerHTML = `<div class="meta error">SQL vacio.</div>`; return; }
    result.innerHTML = `<div class="meta">Ejecutando...</div>`;
    try {
      const res = await window.api.query(trimmed, allowDestructive);
      pushHistory(trimmed);
      renderHistory();
      renderResult(res);
    } catch (err) {
      result.innerHTML = `<div class="meta error">❌ ${escapeHtml(err.message || "Error")}</div>`;
    }
  }

  function renderResult(res) {
    const root = document.getElementById("sql-result");
    const { columns, rows, rowcount, duration_ms } = res;
    const metaHtml = `<div class="meta success">✓ ${rowcount} filas afectadas — ${duration_ms.toFixed(1)} ms</div>`;
    if (!columns.length) {
      root.innerHTML = metaHtml;
      return;
    }
    const thead = columns.map(c => `<th>${escapeHtml(c)}</th>`).join("");
    const tbody = rows.map(r =>
      `<tr>${columns.map(c => `<td>${formatCellValue(r[c])}</td>`).join("")}</tr>`
    ).join("") || `<tr><td colspan="${columns.length}" style="color:var(--text-muted); text-align:center; padding:1rem;">Sin filas.</td></tr>`;
    root.innerHTML = `
      ${metaHtml}
      <div style="overflow:auto; max-height:calc(100% - 40px);">
        <table class="grid">
          <thead><tr>${thead}</tr></thead>
          <tbody>${tbody}</tbody>
        </table>
      </div>`;
  }

  return { init };
})();
