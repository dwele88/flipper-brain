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
    const o2 = o.cloneNode(true);
    $("brain-mood").appendChild(o2);
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

/* ---------------- eyes + ears (bridge only) ---------------- */
let eyesStream = null, eyesTimer = null, earsStream = null, earsTimer = null;
let earsCtx = null, earsAnalyser = null;
const eyesVideo = $("eyes-video"), eyesCanvas = $("eyes-canvas");
const ectx = eyesCanvas.getContext("2d", { willReadFrequently: true });

function gray48x36() {
  ectx.drawImage(eyesVideo, 0, 0, 48, 36);
  const d = ectx.getImageData(0, 0, 48, 36).data;
  const px = new Uint8Array(48 * 36);
  for (let i = 0; i < px.length; i++)
    px[i] = (d[i*4]*0.299 + d[i*4+1]*0.587 + d[i*4+2]*0.114) | 0;
  return px;
}
function b64(bytes) {
  let s = "";
  for (let i = 0; i < bytes.length; i += 8192)
    s += String.fromCharCode.apply(null, bytes.subarray(i, i + 8192));
  return btoa(s);
}
async function captureEyeFrame() {
  if (eyesVideo.readyState < 2) return;
  try {
    const r = await api("/api/eyes/frame", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ t: Date.now() / 1000, w: 48, h: 36,
                             px: b64(gray48x36()) }),
    });
    if (!r.ok) return;
    $("m-bright").style.width = (r.brightness * 100) + "%";
    $("m-motion").style.width = (r.motion * 100) + "%";
    const z = $("eyes-zones");
    if (!z.children.length)
      for (let i = 0; i < 9; i++) z.appendChild(document.createElement("i"));
    r.zones.forEach((v, i) => {
      const g = Math.round(v * 255);
      z.children[i].style.background = `rgb(${g},${g},${g})`;
    });
    const dark = r.brightness < 0.15 ? "dark" : r.brightness > 0.75 ? "bright" : "dim";
    $("eyes-status").textContent =
      `👁 seeing — ${dark}, motion ${(r.motion * 100) | 0}%`;
  } catch (e) { /* bridge hiccup; next frame retries */ }
}
$("btn-eyes").onclick = async () => {
  if (eyesStream) {
    clearInterval(eyesTimer); eyesTimer = null;
    eyesStream.getTracks().forEach((t) => t.stop()); eyesStream = null;
    eyesVideo.style.display = "none";
    $("btn-eyes").textContent = "👁 Enable eyes";
    $("eyes-status").textContent = "Eyes off. The brain can't see until you enable them.";
    return;
  }
  if (!bridgeActive()) { alert("Eyes need the Bridge transport."); return; }
  if (!navigator.mediaDevices?.getUserMedia) {
    $("eyes-status").textContent = "Camera not available in this browser.";
    return;
  }
  try {
    eyesStream = await navigator.mediaDevices.getUserMedia(
      { video: { facingMode: "environment", width: 320 }, audio: false });
    eyesVideo.srcObject = eyesStream;
    eyesVideo.play();
    eyesVideo.style.display = "";
    $("btn-eyes").textContent = "👁 Disable eyes";
    eyesTimer = setInterval(captureEyeFrame, 1000);
    mascotEvent("curious");
  } catch (e) {
    $("eyes-status").textContent = "Camera blocked: " + e.message;
  }
};

function earsSample() {
  const n = earsAnalyser.frequencyBinCount;
  const freq = new Uint8Array(n), td = new Uint8Array(earsAnalyser.fftSize);
  earsAnalyser.getByteFrequencyData(freq);
  earsAnalyser.getByteTimeDomainData(td);
  let sum = 0;
  for (let i = 0; i < td.length; i++) { const v = (td[i] - 128) / 128; sum += v * v; }
  const level = Math.min(1, Math.sqrt(sum / td.length) * 3);
  const band = (a, b) => {
    let s = 0; for (let i = a; i < b && i < n; i++) s += freq[i];
    return s / ((b - a) * 255);
  };
  return { level, bass: band(1, 8), mid: band(8, 40), treble: band(40, 100) };
}
async function captureEarSample() {
  try {
    const s = earsSample();
    $("m-level").style.width = (s.level * 100) + "%";
    const r = await api("/api/ears", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ t: Date.now() / 1000, ...s }),
    });
    if (r.ok && r.level > 0.7)
      $("eyes-note").textContent = "🔊 loud! the brain noticed.";
    else if (r.ok && r.level < 0.08)
      $("eyes-note").textContent = "🤫 quiet…";
  } catch (e) { /* next second retries */ }
}
$("btn-ears").onclick = async () => {
  if (earsStream) {
    clearInterval(earsTimer); earsTimer = null;
    earsStream.getTracks().forEach((t) => t.stop()); earsStream = null;
    if (earsCtx) { earsCtx.close(); earsCtx = null; }
    $("btn-ears").textContent = "👂 Enable ears";
    return;
  }
  if (!bridgeActive()) { alert("Ears need the Bridge transport."); return; }
  if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext) {
    $("eyes-note").textContent = "Microphone/audio not available in this browser.";
    return;
  }
  try {
    earsStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    earsCtx = new AudioContext();
    const src = earsCtx.createMediaStreamSource(earsStream);
    earsAnalyser = earsCtx.createAnalyser();
    earsAnalyser.fftSize = 256;
    src.connect(earsAnalyser);
    $("btn-ears").textContent = "👂 Disable ears";
    earsTimer = setInterval(captureEarSample, 1000);
    mascotEvent("curious");
  } catch (e) {
    $("eyes-note").textContent = "Microphone blocked: " + e.message;
  }
};

/* ---------------- remote: d-pad + brain control + voice ---------------- */
document.querySelectorAll(".dpad button").forEach((b) => {
  b.onclick = async () => {
    if (!bridgeActive()) { alert("Remote needs the Bridge transport."); return; }
    const r = await api("/api/input", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: b.dataset.key }),
    });
    // 501 is the honest answer until a real injection path is verified.
    $("remote-note").textContent = r.ok ? "sent ✓"
      : "⚠ " + (r.error || "not available");
  };
});
$("btn-brain-mood").onclick = async () => {
  if (!bridgeActive()) { alert("Remote needs the Bridge transport."); return; }
  const mood = $("brain-mood").value;
  const r = await api("/api/brain", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "mood", mood }),
  });
  if (r.ok) { setMascotMood(mood === "surprise" ? null : mood); mascotEvent("happy"); refreshBridgeStatus(); }
  else alert("Could not switch mood: " + r.error);
};
$("btn-brain-trigger").onclick = async () => {
  if (!bridgeActive()) { alert("Remote needs the Bridge transport."); return; }
  const r = await api("/api/brain", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "trigger" }),
  });
  if (r.ok) mascotEvent("curious");
  else alert("Trigger failed: " + (r.error || "is the playground running?"));
};
async function brainSay() {
  const text = $("brain-say").value.trim();
  if (!text || !bridgeActive()) return;
  $("brain-say").value = "";
  await api("/api/brain", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "speak", text }),
  });
  mascotEvent("happy");
}
$("btn-brain-say").onclick = brainSay;
$("brain-say").addEventListener("keydown", (e) => { if (e.key === "Enter") brainSay(); });

/* voice: push-to-talk in, speechSynthesis out */
let voiceMuted = false, rec = null, recActive = false;
$("btn-mute").onclick = () => {
  voiceMuted = !voiceMuted;
  $("btn-mute").textContent = voiceMuted ? "🔇 voice off" : "🔊 voice on";
  if (voiceMuted) speechSynthesis.cancel();
};
function speakReply(text) {
  if (voiceMuted || !("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.15; u.pitch = 1.3;
  speechSynthesis.speak(u);
}
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SR) {
  $("voice-status").textContent = "Voice input isn't supported in this browser — Chrome/Android only.";
  $("btn-voice").disabled = true;
} else {
  rec = new SR();
  rec.lang = "en-US"; rec.interimResults = false; rec.maxAlternatives = 1;
  rec.onresult = async (ev) => {
    const text = ev.results[0][0].transcript;
    $("voice-status").textContent = `you said: "${text}" — thinking…`;
    try {
      const r = await api("/api/voice", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (r.ok) {
        $("voice-status").textContent = `🧠 ${r.reply}`;
        mascotEvent("happy");
        speakReply(r.reply);
      } else {
        $("voice-status").textContent = "hmm, that didn't work: " + r.error;
      }
    } catch (e) { $("voice-status").textContent = "voice error: " + e.message; }
    recActive = false;
    $("btn-voice").textContent = "🎙 Hold to talk";
  };
  rec.onend = () => {
    if (recActive) { recActive = false; $("btn-voice").textContent = "🎙 Hold to talk"; }
  };
  rec.onerror = (ev) => {
    $("voice-status").textContent = "mic error: " + ev.error;
    recActive = false; $("btn-voice").textContent = "🎙 Hold to talk";
  };
  const vbtn = $("btn-voice");
  const startRec = (e) => {
    e.preventDefault();
    if (!bridgeActive()) { alert("Voice needs the Bridge transport."); return; }
    if (recActive) return;
    recActive = true;
    vbtn.textContent = "🎙 Listening… release";
    $("voice-status").textContent = "listening…";
    try { rec.start(); } catch (err) { recActive = false; }
  };
  const stopRec = () => { if (recActive) { try { rec.stop(); } catch (e) {} } };
  vbtn.addEventListener("pointerdown", startRec);
  vbtn.addEventListener("pointerup", stopRec);
  vbtn.addEventListener("pointerleave", stopRec);
}

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
