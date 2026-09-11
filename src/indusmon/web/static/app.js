/* IndusMon dashboard */
const state = {
  devices: [],
  latest: {},
  selected: null,
  chart: null,
  es: null,
};

function $(id) { return document.getElementById(id); }

function fmt(n, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return Number(n).toFixed(digits);
}

function fmtTime(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleTimeString();
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function buildTagKey(d, t) { return `${d.id}::${t.name}`; }

function renderDevices() {
  const box = $("device-list");
  const sel = $("tag-select");
  const prev = sel.value;
  sel.innerHTML = "";
  box.innerHTML = "";
  if (!state.devices.length) {
    box.innerHTML = '<div class="empty">暂无设备</div>';
    return;
  }
  for (const d of state.devices) {
    const card = document.createElement("div");
    card.className = "device-card";
    const head = document.createElement("h3");
    head.innerHTML = `<span>${d.name}</span><span>${d.id} · unit ${d.unit_id}</span>`;
    card.appendChild(head);
    for (const t of d.tags) {
      const key = buildTagKey(d, t);
      const row = document.createElement("div");
      row.className = "tag-row";
      row.dataset.key = key;
      row.innerHTML = `
        <div class="name"><span class="dot ok" data-dot></span>${t.name}</div>
        <div class="val" data-val>—</div>
        <div class="unit">${t.unit || ""}</div>`;
      row.addEventListener("click", () => {
        state.selected = { device_id: d.id, tag: t.name, key };
        sel.value = key;
        loadHistory();
      });
      card.appendChild(row);
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = `${d.id} / ${t.name}`;
      sel.appendChild(opt);
    }
    box.appendChild(card);
  }
  if (prev && [...sel.options].some((o) => o.value === prev)) sel.value = prev;
  if (!state.selected && sel.value) {
    const [device_id, tag] = sel.value.split("::");
    state.selected = { device_id, tag, key: sel.value };
  }
  paintLatest();
}

function paintLatest() {
  for (const [key, p] of Object.entries(state.latest)) {
    const row = document.querySelector(`.tag-row[data-key="${CSS.escape(key)}"]`);
    if (!row) continue;
    row.querySelector("[data-val]").textContent = fmt(p.value, 2);
  }
}

function ensureChart() {
  const ctx = $("chart").getContext("2d");
  if (state.chart) return state.chart;
  state.chart = new Chart(ctx, {
    type: "line",
    data: { labels: [], datasets: [{ label: "value", data: [], borderColor: "#2dd4bf", backgroundColor: "rgba(45,212,191,0.12)", tension: 0.2, pointRadius: 0, borderWidth: 2 }] },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: { ticks: { color: "#8b9bab", maxTicksLimit: 8 }, grid: { color: "#243041" } },
        y: { ticks: { color: "#8b9bab" }, grid: { color: "#243041" } },
      },
      plugins: { legend: { display: false } },
    },
  });
  return state.chart;
}

async function loadHistory() {
  if (!state.selected) return;
  const range = Number($("range-select").value);
  const to = Date.now();
  const from = to - range;
  const q = new URLSearchParams({
    device_id: state.selected.device_id,
    tag: state.selected.tag,
    from: String(from),
    to: String(to),
  });
  try {
    const data = await api(`/api/v1/series?${q}`);
    const chart = ensureChart();
    chart.data.labels = data.points.map((p) => fmtTime(p.ts));
    chart.data.datasets[0].label = `${state.selected.device_id}/${state.selected.tag}`;
    chart.data.datasets[0].data = data.points.map((p) => p.value);
    chart.update("none");
  } catch (err) {
    console.error(err);
  }
}

function appendLive(p) {
  if (!state.selected) return;
  if (p.device_id !== state.selected.device_id || p.tag !== state.selected.tag) return;
  const chart = ensureChart();
  chart.data.labels.push(fmtTime(p.ts));
  chart.data.datasets[0].data.push(p.value);
  const max = 120;
  if (chart.data.labels.length > max) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }
  chart.update("none");
}

async function refreshAlerts() {
  const alerts = await api("/api/v1/alerts?limit=50");
  const box = $("alert-list");
  const active = alerts.filter((a) => a.state === "active").length;
  $("alert-count").textContent = String(active);
  box.innerHTML = "";
  if (!alerts.length) {
    box.innerHTML = '<div class="empty">暂无告警</div>';
    return;
  }
  for (const a of alerts) {
    const item = document.createElement("div");
    item.className = `alert-item ${a.state}`;
    item.innerHTML = `
      <div>
        <div><span class="lv ${a.level}">${a.level.toUpperCase()}</span> · ${a.device_id}/${a.tag}</div>
        <div style="color:#8b9bab">${fmtTime(a.ts)} · value=${fmt(a.value)} limit=${fmt(a.limit)} · ${a.state}</div>
      </div>`;
    if (a.state === "active") {
      const btn = document.createElement("button");
      btn.className = "btn";
      btn.textContent = "ACK";
      btn.addEventListener("click", async () => {
        await api(`/api/v1/alerts/${a.id}/ack`, { method: "POST" });
        refreshAlerts();
      });
      item.appendChild(btn);
    }
    box.appendChild(item);
  }
}

async function refreshMetrics() {
  const m = await api("/api/v1/metrics");
  $("metrics").innerHTML = `采集轮次 ${m.poll_rounds}<br>写入点数 ${m.points_written}<br>通信错误 ${m.comm_errors}<br>启用设备 ${m.devices_enabled} · 活动告警 ${m.active_alerts}`;
}

function connectSSE() {
  if (state.es) state.es.close();
  const es = new EventStream("/api/v1/stream");
  state.es = es;
  es.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    for (const p of data.readings || []) {
      const key = `${p.device_id}::${p.tag}`;
      state.latest[key] = p;
      appendLive(p);
    }
    paintLatest();
  };
}

async function spike() {
  if (!state.selected) return;
  const raw = prompt("尖峰值（工程量）", "200");
  if (raw === null) return;
  await api("/api/v1/sim/spike", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      device_id: state.selected.device_id,
      tag: state.selected.tag,
      value: Number(raw),
      duration_s: 8,
    }),
  });
  setTimeout(refreshAlerts, 1500);
}

async function boot() {
  state.devices = await api("/api/v1/devices");
  renderDevices();
  await loadHistory();
  await refreshAlerts();
  await refreshMetrics();
  connectSSE();
  $("tag-select").addEventListener("change", (e) => {
    const [device_id, tag] = e.target.value.split("::");
    state.selected = { device_id, tag, key: e.target.value };
    loadHistory();
  });
  $("range-select").addEventListener("change", loadHistory);
  $("btn-refresh").addEventListener("click", loadHistory);
  $("btn-spike").addEventListener("click", spike);
  setInterval(refreshAlerts, 3000);
  setInterval(refreshMetrics, 2000);
  setInterval(loadHistory, 15000);
}

boot().catch((err) => {
  document.body.insertAdjacentHTML("beforeend", `<pre style="color:#f87171;padding:16px">${err}</pre>`);
});
