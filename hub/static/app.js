"use strict";

// ---- config ---------------------------------------------------------------
const PAD = 36;          // svg padding (user units)
const VIEW_W = 1000;     // svg coordinate width
const LANE_PX = 5;       // perpendicular spacing between parallel lines
const STATION_R = 3.4;
const INTERCHANGE_R = 5.2;
const TRAIN_R = 4.2;
const EASE = 0.18;       // per-frame easing toward target position

const LINE_NAMES = {
  RD: "Red", BL: "Blue", OR: "Orange", SV: "Silver", GR: "Green", YL: "Yellow",
};

const SVGNS = "http://www.w3.org/2000/svg";

// ---- state ----------------------------------------------------------------
let geo = null;          // geometry payload
let project = null;      // (lat,lon) -> {x,y}
let stationXY = {};      // code -> {x,y}
let trainDots = {};      // id -> {el, curX, curY, tgtX, tgtY}
let activeStation = null;

const $ = (sel) => document.querySelector(sel);

// ---- projection -----------------------------------------------------------
// Stations carry schematic grid coords (x, y); fit them into the SVG viewBox.
function buildProjection(stations) {
  const xs = stations.map((s) => s.x).filter((v) => v != null);
  const ys = stations.map((s) => s.y).filter((v) => v != null);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const gridW = xMax - xMin || 1;
  const gridH = yMax - yMin || 1;
  const drawW = VIEW_W - 2 * PAD;
  const scale = drawW / gridW;
  const drawH = gridH * scale;
  const viewH = drawH + 2 * PAD;

  $("#map").setAttribute("viewBox", `0 0 ${VIEW_W} ${viewH}`);

  project = (x, y) => ({
    x: PAD + (x - xMin) * scale,
    y: PAD + (y - yMin) * scale,
  });
}

// ---- geometry helpers -----------------------------------------------------
function perp(ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay;
  const len = Math.hypot(dx, dy) || 1;
  return { x: -dy / len, y: dx / len };
}

// Offset each polyline vertex along the average normal of its adjacent segments.
function offsetPolyline(points, lane) {
  if (!lane) return points;
  const out = [];
  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    const a = points[i - 1] || p;
    const b = points[i + 1] || p;
    let nx = 0, ny = 0;
    if (points[i - 1]) { const n = perp(a.x, a.y, p.x, p.y); nx += n.x; ny += n.y; }
    if (points[i + 1]) { const n = perp(p.x, p.y, b.x, b.y); nx += n.x; ny += n.y; }
    const len = Math.hypot(nx, ny) || 1;
    out.push({ x: p.x + (nx / len) * lane * LANE_PX, y: p.y + (ny / len) * lane * LANE_PX });
  }
  return out;
}

// ---- rendering: lines + stations -----------------------------------------
function renderGeometry() {
  buildProjection(geo.stations);

  for (const s of geo.stations) {
    if (s.x != null) stationXY[s.code] = project(s.x, s.y);
  }

  const linesLayer = $("#lines-layer");
  for (const line of geo.lines) {
    const pts = line.stations.map((c) => stationXY[c]).filter(Boolean);
    const off = offsetPolyline(pts, line.lane);
    const d = off.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
    const path = document.createElementNS(SVGNS, "path");
    path.setAttribute("d", d);
    path.setAttribute("class", "line-path");
    path.setAttribute("stroke", line.color);
    path.setAttribute("stroke-width", "3.4");
    linesLayer.appendChild(path);
  }

  const stationsLayer = $("#stations-layer");
  for (const s of geo.stations) {
    const p = stationXY[s.code];
    if (!p) continue;
    const interchange = (s.lines.length > 1) || (s.together && s.together.length);
    const dot = document.createElementNS(SVGNS, "circle");
    dot.setAttribute("cx", p.x.toFixed(1));
    dot.setAttribute("cy", p.y.toFixed(1));
    dot.setAttribute("r", interchange ? INTERCHANGE_R : STATION_R);
    dot.setAttribute("class", "station-dot" + (interchange ? " interchange" : ""));
    dot.dataset.code = s.code;
    dot.dataset.name = s.name;
    dot.dataset.together = (s.together || []).join(",");
    const title = document.createElementNS(SVGNS, "title");
    title.textContent = s.name;
    dot.appendChild(title);
    dot.addEventListener("click", () => selectStation(s));
    stationsLayer.appendChild(dot);
  }

  renderLegend();
}

function renderLegend() {
  const legend = $("#legend");
  legend.innerHTML = "";
  for (const line of geo.lines) {
    const item = document.createElement("div");
    item.className = "legend-item";
    item.innerHTML =
      `<span class="legend-swatch" style="background:${line.color}"></span>${LINE_NAMES[line.code] || line.code}`;
    legend.appendChild(item);
  }
}

// ---- rendering: trains (animated) ----------------------------------------
function trainScreenPos(t) {
  const a = stationXY[t.from], b = stationXY[t.to];
  if (!a) return null;
  if (!b || t.from === t.to) return { x: a.x, y: a.y };
  // Interpolate along the schematic segment, then offset onto the line's lane.
  const f = t.frac == null ? 0 : t.frac;
  const base = { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f };
  const lane = laneFor(t.line);
  if (!lane) return base;
  const n = perp(a.x, a.y, b.x, b.y);
  return { x: base.x + n.x * lane * LANE_PX, y: base.y + n.y * lane * LANE_PX };
}

function laneFor(code) {
  const line = geo.lines.find((l) => l.code === code);
  return line ? line.lane : 0;
}

function updateTrains(trains) {
  const seen = new Set();
  const layer = $("#trains-layer");
  for (const t of trains) {
    const pos = trainScreenPos(t);
    if (!pos) continue;
    seen.add(t.id);
    let dot = trainDots[t.id];
    if (!dot) {
      const el = document.createElementNS(SVGNS, "circle");
      el.setAttribute("r", TRAIN_R);
      el.setAttribute("class", "train-dot");
      el.setAttribute("fill", t.color);
      const title = document.createElementNS(SVGNS, "title");
      el.appendChild(title);
      layer.appendChild(el);
      dot = trainDots[t.id] = { el, curX: pos.x, curY: pos.y, tgtX: pos.x, tgtY: pos.y, title };
    }
    dot.tgtX = pos.x;
    dot.tgtY = pos.y;
    dot.el.setAttribute("fill", t.color);
    dot.title.textContent = `${LINE_NAMES[t.line] || t.line} → ${t.dest}`;
  }
  // Remove trains that vanished.
  for (const id of Object.keys(trainDots)) {
    if (!seen.has(id)) {
      trainDots[id].el.remove();
      delete trainDots[id];
    }
  }
  $("#train-count").textContent = `${seen.size} trains`;
}

function animate() {
  for (const id in trainDots) {
    const d = trainDots[id];
    d.curX += (d.tgtX - d.curX) * EASE;
    d.curY += (d.tgtY - d.curY) * EASE;
    d.el.setAttribute("cx", d.curX.toFixed(2));
    d.el.setAttribute("cy", d.curY.toFixed(2));
  }
  requestAnimationFrame(animate);
}

// ---- arrival board --------------------------------------------------------
function selectStation(s) {
  activeStation = s;
  document.querySelectorAll(".station-dot.active").forEach((e) => e.classList.remove("active"));
  document.querySelectorAll(`.station-dot[data-code="${s.code}"]`).forEach((e) => e.classList.add("active"));
  $("#board-title").textContent = s.name;
  const codes = [s.code, ...(s.together || [])].join(",");
  $("#board-sub").textContent = "Loading…";
  loadArrivals(codes);
}

async function loadArrivals(codes) {
  try {
    const r = await fetch(`/api/arrivals?codes=${encodeURIComponent(codes)}`);
    const data = await r.json();
    const trains = data.stations.flatMap((st) => st.trains);
    renderBoard(trains);
  } catch (e) {
    $("#board-sub").textContent = "Could not load arrivals.";
  }
}

function colorFor(code) {
  const line = geo.lines.find((l) => l.code === code);
  return line ? line.color : "#888";
}

function renderBoard(trains) {
  const list = $("#board-list");
  list.innerHTML = "";
  const valid = trains.filter((t) => t.dest && t.dest !== "No Passenger" && t.dest !== "Train");
  $("#board-sub").textContent = valid.length ? `${valid.length} upcoming` : "No trains reported";
  for (const t of valid) {
    const li = document.createElement("li");
    const min = t.min;
    const minHtml = (min === "ARR" || min === "BRD")
      ? `${min}`
      : `${min}<small> min</small>`;
    li.innerHTML =
      `<span class="pill" style="background:${colorFor(t.line)}">${t.line || ""}</span>` +
      `<span class="board-dest">${t.dest}</span>` +
      `<span class="board-min">${minHtml}</span>`;
    list.appendChild(li);
  }
}

// ---- incident ticker ------------------------------------------------------
async function loadIncidents() {
  try {
    const r = await fetch("/api/incidents");
    const data = await r.json();
    const items = [];
    for (const inc of data.rail) {
      items.push(`<span class="ticker-item"><b>${(inc.lines || []).join(" ")}</b> ${inc.description}</span>`);
    }
    for (const e of data.elevator) {
      items.push(`<span class="ticker-item"><b>${e.unit}</b> @ ${e.station} — ${e.symptom}</span>`);
    }
    if (!items.length) items.push(`<span class="ticker-item clear">No service incidents reported — trains running normally.</span>`);
    $("#ticker").innerHTML = `<div id="ticker-inner">${items.join("")}</div>`;
  } catch (e) { /* leave previous */ }
}

// ---- polling --------------------------------------------------------------
async function poll(url, onData) {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(r.status);
    onData(await r.json());
    setConn(true);
  } catch (e) {
    setConn(false);
  }
}

function setConn(ok) {
  const el = $("#conn");
  el.textContent = ok ? "connected" : "reconnecting…";
  el.className = ok ? "ok" : "bad";
}

function tickClock() {
  const d = new Date();
  $("#clock").textContent = d.toLocaleTimeString([], { hour12: false });
}

// ---- boot -----------------------------------------------------------------
async function boot() {
  setInterval(tickClock, 1000);
  tickClock();

  const r = await fetch("/api/geometry");
  geo = await r.json();
  renderGeometry();
  animate();

  // Default focus: Metro Center if present, else first interchange.
  const metro = geo.stations.find((s) => s.code === "A01")
    || geo.stations.find((s) => s.lines.length > 1)
    || geo.stations[0];
  if (metro) selectStation(metro);

  const pollTrains = () => poll("/api/trains", (d) => updateTrains(d.trains));
  pollTrains();
  setInterval(pollTrains, 10000);

  loadIncidents();
  setInterval(loadIncidents, 30000);

  setInterval(() => {
    if (activeStation) {
      const codes = [activeStation.code, ...(activeStation.together || [])].join(",");
      loadArrivals(codes);
    }
  }, 15000);
}

boot();
