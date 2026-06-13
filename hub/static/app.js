"use strict";

// ---- config ---------------------------------------------------------------
const SVGNS = "http://www.w3.org/2000/svg";
const ROW_H = 64;          // vertical spacing between line strips
const TOP_PAD = 30;
const LEFT_PAD = 116;      // room for the line bullet + label
const RIGHT_PAD = 36;
const STATION_R = 3.2;
const INTERCHANGE_R = 4.6;
const TRAIN_R = 5;
const EASE = 0.16;         // per-frame easing for gliding trains

const LINE_ORDER = ["RD", "OR", "SV", "BL", "YL", "GR"];
const LINE_NAMES = {
  RD: "Red", OR: "Orange", SV: "Silver", BL: "Blue", GR: "Green", YL: "Yellow",
};

const $ = (s) => document.querySelector(s);

// ---- state ----------------------------------------------------------------
let geo = null;
let lines = [];            // ordered line objects from geo
let lineIndex = {};        // code -> row index
let stationPos = {};       // `${code}@${line}` -> {x, y}
let stationMeta = {};      // code -> station object
let trainDots = {};        // id -> {el, curX, curY, tgtX, tgtY, title}
let boards = [];           // {code, name, codes, pinned, el, listEl}
const POLL = {};

// ---- layout ---------------------------------------------------------------
function lineRowY(i) { return TOP_PAD + i * ROW_H; }

function buildLayout() {
  const svg = $("#map");
  const width = $("#map-section").clientWidth || 1000;
  const height = TOP_PAD + (lines.length - 1) * ROW_H + TOP_PAD;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", width);
  svg.setAttribute("height", height);

  const trackW = width - LEFT_PAD - RIGHT_PAD;

  lines.forEach((line, i) => {
    const y = lineRowY(i);
    const n = line.stations.length;
    line.stations.forEach((code, k) => {
      const x = LEFT_PAD + (n === 1 ? 0 : (k / (n - 1)) * trackW);
      stationPos[`${code}@${line.code}`] = { x, y };
    });
  });
}

function stationFrac(code, lineCode) {
  const line = lines[lineIndex[lineCode]];
  if (!line) return null;
  const k = line.stations.indexOf(code);
  if (k < 0) return null;
  return k / Math.max(1, line.stations.length - 1);
}

// ---- rendering: tracks, links, stations -----------------------------------
function canonical(code) {
  const s = stationMeta[code];
  if (!s) return code;
  return [code, ...(s.together || [])].sort()[0];
}

function render() {
  buildLayout();
  const width = $("#map").viewBox.baseVal.width;
  const trackW = width - LEFT_PAD - RIGHT_PAD;

  const tracks = $("#tracks-layer");
  const stationsLayer = $("#stations-layer");
  const links = $("#links-layer");

  // Interchange links (git-branch style curves between strips).
  const groups = {};
  lines.forEach((line, i) => {
    for (const code of line.stations) {
      const s = stationMeta[code];
      const isX = s && ((s.lines && s.lines.length > 1) || (s.together && s.together.length));
      if (!isX) continue;
      const key = canonical(code);
      (groups[key] = groups[key] || []).push({ i, pos: stationPos[`${code}@${line.code}`] });
    }
  });
  for (const key in groups) {
    const members = groups[key].sort((a, b) => a.i - b.i);
    for (let m = 1; m < members.length; m++) {
      const a = members[m - 1].pos, b = members[m].pos;
      const midY = (a.y + b.y) / 2;
      const d = `M${a.x} ${a.y} C ${a.x} ${midY}, ${b.x} ${midY}, ${b.x} ${b.y}`;
      const path = document.createElementNS(SVGNS, "path");
      path.setAttribute("d", d);
      path.setAttribute("class", "xfer-link");
      links.appendChild(path);
    }
  }

  // Tracks, labels, station ticks.
  lines.forEach((line, i) => {
    const y = lineRowY(i);
    const x0 = LEFT_PAD, x1 = LEFT_PAD + trackW;

    const track = document.createElementNS(SVGNS, "line");
    track.setAttribute("x1", x0); track.setAttribute("y1", y);
    track.setAttribute("x2", x1); track.setAttribute("y2", y);
    track.setAttribute("class", "track");
    track.setAttribute("stroke", line.color);
    tracks.appendChild(track);

    // Line bullet + name on the left.
    const bullet = document.createElementNS(SVGNS, "circle");
    bullet.setAttribute("cx", 24); bullet.setAttribute("cy", y);
    bullet.setAttribute("r", 11); bullet.setAttribute("fill", line.color);
    tracks.appendChild(bullet);
    const blab = document.createElementNS(SVGNS, "text");
    blab.setAttribute("x", 42); blab.setAttribute("y", y + 4);
    blab.setAttribute("class", "line-name");
    blab.textContent = LINE_NAMES[line.code] || line.code;
    tracks.appendChild(blab);

    for (const code of line.stations) {
      const p = stationPos[`${code}@${line.code}`];
      const s = stationMeta[code];
      const isX = s && ((s.lines && s.lines.length > 1) || (s.together && s.together.length));
      const dot = document.createElementNS(SVGNS, "circle");
      dot.setAttribute("cx", p.x); dot.setAttribute("cy", p.y);
      dot.setAttribute("r", isX ? INTERCHANGE_R : STATION_R);
      dot.setAttribute("class", "station-dot" + (isX ? " interchange" : ""));
      dot.dataset.code = code;
      const title = document.createElementNS(SVGNS, "title");
      title.textContent = s ? s.name : code;
      dot.appendChild(title);
      dot.addEventListener("click", () => openBoard(code));
      stationsLayer.appendChild(dot);
    }
  });
}

// ---- trains ---------------------------------------------------------------
function updateTrains(trains) {
  const layer = $("#trains-layer");
  const seen = new Set();
  for (const t of trains) {
    const f = stationFrac(t.from, t.line);
    if (f == null) continue;
    const fTo = stationFrac(t.to, t.line);
    const frac = fTo == null ? f : f + (fTo - f) * (t.frac == null ? 0 : t.frac);
    const pos = stationPos[`${t.from}@${t.line}`];
    if (!pos) continue;
    const width = $("#map").viewBox.baseVal.width;
    const trackW = width - LEFT_PAD - RIGHT_PAD;
    const x = LEFT_PAD + frac * trackW;
    const y = lineRowY(lineIndex[t.line]);

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
      dot = trainDots[t.id] = { el, curX: x, curY: y, tgtX: x, tgtY: y, title };
    }
    dot.tgtX = x; dot.tgtY = y;
    dot.el.setAttribute("fill", t.color);
    dot.title.textContent = `${LINE_NAMES[t.line] || t.line} → ${t.dest}`;
  }
  for (const id of Object.keys(trainDots)) {
    if (!seen.has(id)) { trainDots[id].el.remove(); delete trainDots[id]; }
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

// ---- arrival boards (click + pin) -----------------------------------------
function colorFor(code) {
  const line = lines.find((l) => l.code === code);
  return line ? line.color : "#888";
}

function openBoard(code) {
  const s = stationMeta[code];
  if (!s) return;
  const codes = [code, ...(s.together || [])];
  // Already shown? just refresh it.
  let board = boards.find((b) => b.code === code || (s.together || []).includes(b.code));
  if (!board) {
    // Replace the existing transient (unpinned) board, if any.
    const transient = boards.find((b) => !b.pinned);
    if (transient) removeBoard(transient);
    board = createBoard(code, s.name, codes);
    boards.push(board);
  }
  loadBoard(board);
  $("#boards-hint").style.display = boards.length ? "none" : "";
}

function createBoard(code, name, codes) {
  const el = document.createElement("div");
  el.className = "board-card";
  el.innerHTML =
    `<div class="board-head">
       <span class="board-name"></span>
       <span class="board-actions">
         <button class="pin-btn" title="Pin">📌</button>
         <button class="close-btn" title="Close">✕</button>
       </span>
     </div>
     <ul class="board-list"></ul>`;
  el.querySelector(".board-name").textContent = name;
  const board = { code, name, codes, pinned: false, el, listEl: el.querySelector(".board-list") };
  el.querySelector(".pin-btn").addEventListener("click", () => togglePin(board));
  el.querySelector(".close-btn").addEventListener("click", () => removeBoard(board));
  $("#boards-grid").appendChild(el);
  return board;
}

function togglePin(board) {
  board.pinned = !board.pinned;
  board.el.classList.toggle("pinned", board.pinned);
  board.el.querySelector(".pin-btn").classList.toggle("on", board.pinned);
}

function removeBoard(board) {
  board.el.remove();
  boards = boards.filter((b) => b !== board);
  $("#boards-hint").style.display = boards.length ? "none" : "";
}

async function loadBoard(board) {
  try {
    const r = await fetch(`/api/arrivals?codes=${encodeURIComponent(board.codes.join(","))}`);
    const data = await r.json();
    const trains = data.stations.flatMap((st) => st.trains)
      .filter((t) => t.dest && t.dest !== "No Passenger" && t.dest !== "Train");
    board.listEl.innerHTML = trains.length
      ? trains.map((t) => {
          const min = (t.min === "ARR" || t.min === "BRD") ? t.min : `${t.min}<small> min</small>`;
          return `<li><span class="pill" style="background:${colorFor(t.line)}">${t.line || ""}</span>` +
                 `<span class="b-dest">${t.dest}</span><span class="b-min">${min}</span></li>`;
        }).join("")
      : `<li class="b-empty">No trains reported</li>`;
  } catch (e) {
    board.listEl.innerHTML = `<li class="b-empty">Could not load arrivals</li>`;
  }
}

function refreshBoards() { boards.forEach(loadBoard); }

// ---- news banner ----------------------------------------------------------
async function loadNews() {
  try {
    const r = await fetch("/api/news");
    const data = await r.json();
    const items = data.items.length ? data.items : [{ kind: "news", text: "No news." }];
    const html = items.map((it) => {
      const tag = it.kind === "alert"
        ? `<b class="n-alert">ALERT</b>` : `<b class="n-news">DC</b>`;
      return `<span class="news-item">${tag} ${it.text}</span>`;
    }).join("");
    $("#news-scroll").innerHTML = `<div id="news-inner">${html}${html}</div>`;
  } catch (e) { /* keep previous */ }
}

// ---- polling / status -----------------------------------------------------
async function poll(url, onData) {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(r.status);
    onData(await r.json());
    setConn(true);
  } catch (e) { setConn(false); }
}

function setConn(ok) {
  const el = $("#conn");
  el.textContent = ok ? "connected" : "reconnecting…";
  el.className = ok ? "ok" : "bad";
}

function tickClock() {
  $("#clock").textContent = new Date().toLocaleTimeString([], { hour12: false });
}

// ---- boot -----------------------------------------------------------------
async function boot() {
  setInterval(tickClock, 1000); tickClock();

  const r = await fetch("/api/geometry");
  geo = await r.json();
  for (const s of geo.stations) stationMeta[s.code] = s;
  lines = LINE_ORDER.map((c) => geo.lines.find((l) => l.code === c)).filter(Boolean);
  lines.forEach((l, i) => (lineIndex[l.code] = i));

  render();
  animate();

  const pollTrains = () => poll("/api/trains", (d) => updateTrains(d.trains));
  pollTrains();
  setInterval(pollTrains, 10000);

  loadNews(); setInterval(loadNews, 60000);
  setInterval(refreshBoards, 15000);

  // Reflow the strip layout on resize (debounced), keeping train/board state.
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(reflow, 250);
  });
}

function reflow() {
  ["links-layer", "tracks-layer", "stations-layer", "trains-layer"].forEach((id) => {
    const g = document.getElementById(id);
    while (g.firstChild) g.removeChild(g.firstChild);
  });
  trainDots = {};
  render();
}

boot();
