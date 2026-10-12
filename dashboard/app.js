/* Flipper Brain dashboard — plain JS, no libraries.
 * All Flipper commands go through FlipperConnection (transport.js).
 * Playground + Library are bridge-server features; they enable only when
 * the active transport is the Bridge. Terminal / Device / Files / Apps
 * work on every transport via the unified CLI surface.
 */
const $ = (id) => document.getElementById(id);
const api = (p, o) => fetch(p, o).then((r) => r.json());
const conn = new FlipperConnection();

/* ---------------- mascot (unchanged behavior) ---------------- */
const mascot = $("mascot");
let idleTimer = null, eventTimer = null;

function setMascotMood(mood) {
  mascot.classList.remove("mood-gremlin", "mood-explorer", "mood-dj", "mood-ghost");
  if (mood) mascot.classList.add("mood-" + mood);
}
function mascotEvent(ev) {
  mascot.classList.remove("is-happy", "is-curious", "is-sleepy");
  if (!ev) return;
  mascot.classList.add("is-" + ev);
  clearTimeout(eventTimer);
  eventTimer = setTimeout(() => {
    mascot.classList.remove("is-happy", "is-curious");
  }, ev === "sleepy" ? 10000 : 2500);
  pokeIdle();
}
function pokeIdle() {
  mascot.classList.remove("is-sleepy");
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => mascot.classList.add("is-sleepy"), 90000);
}

/* intro: captions follow the CSS performance, then the brain moves to its dock */
const captions = ["waking up…", "stretching…", "*looks around*", "oh hey! o/", ""];
captions.forEach((c, i) => setTimeout(() => { $("intro-caption").textContent = c; }, i * 1150));
function endIntro() {
  if ($("intro").classList.contains("hide")) return;
  $("intro").classList.add("hide");
  $("mascot-dock").appendChild(mascot);
  $("mascot-dock").classList.add("show");
  pokeIdle();
}
setTimeout(endIntro, 5800);
$("skip-intro").onclick = endIntro;

/* ---------------- connection ---------------- */
let selectedTransport = "bridge";

function renderTransports() {
  const row = $("transport-row");
  row.innerHTML = "";
  for (const t of FlipperConnection.available()) {
    const b = document.createElement("button");
    b.className = "ghost" + (t.kind === selectedTransport ? " sel" : "");
    b.dataset.kind = t.kind;
    b.innerHTML = "";
    const icons = { bridge: "🖥", bluetooth: "📶", serial: "🔌" };
    b.textContent = `${icons[t.kind] || "•"} ${t.label}`;
    b.title = t.kind === "bridge"
      ? "Local Python bridge over USB (full features)"
      : t.kind === "bluetooth"
      ? "Web Bluetooth straight to the Flipper (Chrome/Android)"
      : "Web Serial over USB (desktop Chrome/Edge only)";
    if (t.kind !== "bridge" && !t.serverFeatures) {
      const tag = document.createElement("small");
      tag.textContent = " no playground";
      b.appendChild(tag);
    }
    b.onclick = () => { selectedTransport = t.kind; renderTransports(); };
    row.appendChild(b);
  }
  const notes = {
    bridge: "Python bridge on this machine — Terminal, Files, Apps, Playground, Library all work.",
    bluetooth: "Pairs straight to the Flipper over BLE. Terminal, Files, Apps work. Playground + Library need the Bridge.",
    serial: "USB serial in the browser (desktop Chrome/Edge). Terminal, Files, Apps work. Playground + Library need the Bridge.",
  };
  $("conn-detail").textContent = notes[selectedTransport] || "";
}

function setConnPill(state, detail) {
  const el = $("conn");
  if (state === "connected") {
    el.textContent = "● " + conn.kind;
    el.classList.add("on");
  } else if (state === "connecting") {
    el.textContent = "◌ connecting…";
    el.classList.remove("on");
  } else {
    el.textContent = "○ disconnected" + (detail ? " — " + detail : "");
    el.classList.remove("on");
  }
}

/* (status handler is registered once, below, after all sections are defined) */

$("btn-connect").onclick = async () => {
  setConnPill("connecting");
  $("conn-detail").textContent = "Connecting…";
  try {
    await conn.connect(selectedTransport);
    $("conn-detail").textContent =
      selectedTransport === "bluetooth"
        ? "Connected over Bluetooth. If commands fail, pair in system Bluetooth settings first."
        : "Connected.";
  } catch (e) {
    $("conn-detail").textContent = "Failed: " + e.message;
  }
};
$("btn-disconnect").onclick = () => conn.disconnect();

/* ---------------- device ---------------- */
$("btn-info").onclick = async () => {
  if (!conn.isConnected()) { $("dev-info").textContent = "not connected"; return; }
  try {
    const info = await conn.deviceInfo();
    $("dev-info").innerHTML =
      `<div class="kv"><span>transport</span><b>${conn.kind}</b></div>` +
      "<pre>" + info.replace(/</g, "&lt;") + "</pre>";
    mascotEvent("happy");
  } catch (e) { $("dev-info").textContent = "error: " + e.message; }
};
$("btn-reboot").onclick = async () => {
  if (!conn.isConnected()) return;
  if (!confirm("Reboot the Flipper?")) return;
  try { await conn.reboot(); } catch (e) {}
  termPrint("reboot sent");
};

/* ---------------- terminal ---------------- */
function termPrint(t) {
  const o = $("term-out");
  o.textContent += t + "\n";
  o.scrollTop = o.scrollHeight;
}
async function termSend() {
  const cmd = $("term-in").value.trim();
  if (!cmd) return;
  if (!conn.isConnected()) { termPrint("ERROR: not connected — Link up first."); return; }
  termPrint("flipper> " + cmd);
  $("term-in").value = "";
  try {
    termPrint(await conn.execCli(cmd));
    mascotEvent("happy");
  } catch (e) { termPrint("ERROR: " + e.message); }
}
$("btn-term").onclick = termSend;
$("term-in").addEventListener("keydown", (e) => { if (e.key === "Enter") termSend(); });

/* ---------------- files ---------------- */
$("btn-ls").onclick = async () => {
  if (!conn.isConnected()) { $("file-list").textContent = "not connected"; return; }
  const path = $("file-path").value.trim() || "/ext";
  try {
    const listing = await conn.storageList(path);
    $("file-list").innerHTML = "<pre>" + listing.replace(/</g, "&lt;") + "</pre>";
  } catch (e) { $("file-list").textContent = "error: " + e.message; }
};

/* ---------------- apps ---------------- */
$("btn-apps").onclick = async () => {
  if (!conn.isConnected()) { $("app-list").textContent = "not connected"; return; }
  const box = $("app-list");
  try {
    const raw = await conn.loaderList();
    box.innerHTML = "";
    raw.split("\n").map((s) => s.trim()).filter(Boolean).slice(0, 60).forEach((name) => {
      const row = document.createElement("div");
      row.className = "arow";
      const label = document.createElement("span");
      label.textContent = name;
      row.appendChild(label);
      const b = document.createElement("button");
      b.textContent = "open";
      b.onclick = async () => {
        try {
          await conn.loaderOpen(name);
          termPrint(`opened ${name}`);
          mascotEvent("happy");
        } catch (e) { termPrint("ERROR: " + e.message); }
      };
      row.appendChild(b);
      box.appendChild(row);
    });
    if (!box.children.length) box.textContent = "(no apps listed)";
  } catch (e) { box.textContent = "error: " + e.message; }
};

/* ---------------- playground (bridge only) ---------------- */
let thoughtCursor = 0;
function bridgeActive() { return conn.kind === "bridge" && conn.isConnected(); }

async function loadMoods() {
  if (!bridgeActive()) return;
  const r = await api("/api/playground/moods");
  const sel = $("pg-mood");
  sel.innerHTML = "";
  for (const [key, m] of Object.entries(r.moods || {})) {
    const o = document.createElement("option");
    o.value = key;
    o.textContent = `${m.emoji} ${m.label} — ${m.description.slice(0, 60)}…`;
    o.title = m.description;
    sel.appendChild(o);
  }
}
$("btn-pg-start").onclick = async () => {
  if (!bridgeActive()) { alert("Playground needs the Bridge transport."); return; }
  const mood = $("pg-mood").value;
  const interval = parseInt($("pg-interval").value, 10) || 20;
  const r = await api("/api/playground/start", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mood, interval }),
  });
  if (!r.ok) alert("Could not start: " + r.error);
  setMascotMood(mood === "surprise" ? null : mood);
  mascotEvent("curious");
  refreshBridgeStatus();
};
$("btn-pg-stop").onclick = async () => {
  if (!bridgeActive()) return;
  await api("/api/playground/stop", { method: "POST" });
  mascotEvent("sleepy");
  refreshBridgeStatus();
};
async function pollThoughts() {
  if (!bridgeActive()) return;
  try {
    const r = await api("/api/playground/thoughts?since=" + thoughtCursor);
    if (!r.ok) return;
    thoughtCursor = r.cursor;
    const box = $("thoughts");
    for (const t of r.thoughts) {
      const div = document.createElement("div");
      div.className = "t";
      const time = new Date(t.ts * 1000).toLocaleTimeString();
      div.innerHTML = `<span class="ts">${time}</span> ` +
        (t.mood ? `<span class="mood">[${t.mood}]</span> ` : "");
      div.appendChild(document.createTextNode(t.text));
      box.appendChild(div);
      box.scrollTop = box.scrollHeight;
      if (t.event) mascotEvent(t.event);
    }
    while (box.children.length > 60) box.removeChild(box.firstChild);
  } catch (e) { /* bridge down */ }
}
async function refreshBridgeStatus() {
  if (!bridgeActive()) { $("pg-status").textContent = "idle (bridge only)"; return; }
  try {
    const s = await api("/api/status");
    const pg = s.playground || {};
    $("pg-status").textContent = pg.running
      ? `running: ${pg.mood} · cycle ${pg.cycle} · every ${pg.interval}s`
      : "idle";
    $("btn-pg-start").disabled = !!pg.running;
    $("btn-pg-stop").disabled = !pg.running;
    if (pg.running) setMascotMood(pg.mood === "surprise" ? null : pg.mood);
    else if (!$("pg-mood").value) setMascotMood(null);
  } catch (e) {}
}

/* ---------------- library (bridge only) ---------------- */
async function loadLibCats() {
  if (!bridgeActive()) return;
  const r = await api("/api/library/categories");
  const sel = $("lib-cat");
  sel.innerHTML = "";
  if (!r.ok) return;
  for (const c of r.categories) {
    const o = document.createElement("option");
    o.value = c.name;
    o.textContent = c.installable ? `${c.name} → ${c.sd_path}` : `${c.name} (browse only)`;
    o.title = c.note;
    sel.appendChild(o);
  }
}
function libRow(file, installable) {
  const row = document.createElement("div");
  row.className = "arow";
  const label = document.createElement("span");
  label.textContent = file.path || file.name;
  label.style.overflow = "hidden";
  label.style.textOverflow = "ellipsis";
  row.appendChild(label);
  if (installable) {
    const b = document.createElement("button");
    b.textContent = "install";
    b.onclick = async () => {
      b.disabled = true; b.textContent = "…";
      const r = await api("/api/library/install", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_path: file.path }),
      });
      termPrint(r.ok
        ? `installed ${r.repo_path} → ${r.sd_path} (${r.bytes} bytes)`
        : "ERROR: " + r.error);
      b.textContent = r.ok ? "done ✓" : "retry";
      b.disabled = !r.ok;
      mascotEvent(r.ok ? "happy" : null);
    };
    row.appendChild(b);
  }
  return row;
}
async function libBrowse() {
  if (!bridgeActive()) { $("lib-list").textContent = "Library needs the Bridge transport."; return; }
  const cat = $("lib-cat").value;
  const box = $("lib-list");
  box.innerHTML = "<div class='t'>loading…</div>";
  const r = await api("/api/library/browse?category=" + encodeURIComponent(cat));
  box.innerHTML = "";
  if (!r.ok) { box.textContent = "error: " + r.error; return; }
  const installable = $("lib-cat").selectedOptions[0].textContent.includes("→");
  r.files.slice(0, 200).forEach((f) => box.appendChild(libRow(f, installable)));
  if (r.files.length > 200)
    box.appendChild(Object.assign(document.createElement("div"),
      { textContent: `…and ${r.files.length - 200} more — use search to narrow`, className: "t" }));
}
async function libSearch() {
  if (!bridgeActive()) { $("lib-list").textContent = "Library needs the Bridge transport."; return; }
  const q = $("lib-q").value.trim();
  if (!q) { libBrowse(); return; }
  const box = $("lib-list");
  box.innerHTML = "<div class='t'>searching…</div>";
  const r = await api("/api/library/search?q=" + encodeURIComponent(q));
  box.innerHTML = "";
  if (!r.ok) { box.textContent = "error: " + r.error; return; }
  r.results.forEach((f) => {
    const top = f.path.split("/")[0];
    const installable = !["GPIO","Graphics","Dolphin_Level","Firmware_Options",
      "Hardware_Troubleshooting","FlipperZero_Dimensions","Wifi_DevBoard",
      "wetox_scripts"].includes(top);
    box.appendChild(libRow(f, installable));
  });
}
$("lib-cat").addEventListener("change", libBrowse);
$("btn-lib-search").onclick = libSearch;
$("lib-q").addEventListener("keydown", (e) => { if (e.key === "Enter") libSearch(); });

/* Status handler — registered once, after all sections are defined. */
conn.onStatus((ev) => {
  setConnPill(ev.state, ev.detail);
  $("btn-connect").disabled = ev.state === "connected" || ev.state === "connecting";
  $("btn-disconnect").disabled = ev.state !== "connected";
  const serverSide = ev.kind === "bridge" && ev.state === "connected";
  document.querySelectorAll(".bridge-only-hint").forEach((el) => {
    el.style.display = serverSide ? "none" : "";
  });
  $("dev-info").innerHTML = ev.state === "connected"
    ? `<div class="kv"><span>transport</span><b>${ev.kind}</b></div>`
    : `<div class="kv"><span>status</span><b>…</b></div>`;
  if (ev.state === "connected") {
    mascotEvent("happy");
    if (ev.kind === "bridge") { loadMoods(); loadLibCats().then(libBrowse); refreshBridgeStatus(); }
  }
  if (ev.state === "disconnected") { $("pg-status").textContent = "idle"; setMascotMood(null); }
});

/* ---------------- boot ---------------- */
renderTransports();
setInterval(refreshBridgeStatus, 5000);
setInterval(pollThoughts, 2000);
pokeIdle();
