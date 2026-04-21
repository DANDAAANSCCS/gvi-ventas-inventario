// admin-web/js/charts.js — Wrapper minimo sobre Chart.js (CDN global `Chart`)

const CHART_COLORS = {
  primary: "#4f46e5",
  primarySoft: "rgba(79, 70, 229, 0.2)",
  success: "#10b981",
  successSoft: "rgba(16, 185, 129, 0.2)",
  warning: "#f59e0b",
  danger: "#ef4444",
  info: "#0ea5e9",
  gray: "#6b7280",
};

function ensureChart() {
  if (typeof window.Chart === "undefined") {
    throw new Error("Chart.js no esta cargado. Incluye el CDN en la pagina.");
  }
}

/** Bar chart. data = { labels: [], values: [] }. */
function renderBarChart(canvas, data, { label = "", color = CHART_COLORS.primary } = {}) {
  ensureChart();
  if (canvas._chart) canvas._chart.destroy();
  canvas._chart = new Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [{
        label,
        data: data.values,
        backgroundColor: color,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: !!label } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
  return canvas._chart;
}

/** Line chart. data = { labels: [], values: [] }. */
function renderLineChart(canvas, data, { label = "", color = CHART_COLORS.primary } = {}) {
  ensureChart();
  if (canvas._chart) canvas._chart.destroy();
  canvas._chart = new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels: data.labels,
      datasets: [{
        label,
        data: data.values,
        borderColor: color,
        backgroundColor: CHART_COLORS.primarySoft,
        fill: true,
        tension: 0.3,
        pointRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: !!label } },
      scales: { y: { beginAtZero: true } },
    },
  });
  return canvas._chart;
}

/** Horizontal bar chart (para top productos). */
function renderHBarChart(canvas, data, { label = "", color = CHART_COLORS.success } = {}) {
  ensureChart();
  if (canvas._chart) canvas._chart.destroy();
  canvas._chart = new Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [{
        label,
        data: data.values,
        backgroundColor: color,
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: !!label } },
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
  return canvas._chart;
}
