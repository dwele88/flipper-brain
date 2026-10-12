function panicTrebleRatio(s) {
  const d = (s.bass || 0) + (s.mid || 0) + (s.treble || 0) + 1e-6;
  return (s.treble || 0) / d;
}
function detectScream(hist) {
  // hist: [{t, level, tr}] ascending by t. A scream is loud (level > 0.75)
  // AND treble-dominant (tr > 0.5), sustained continuously for >= 1500ms.
  // Short claps fail the sustain test; laughter fails the treble test.
  if (!hist || hist.length < 5) return null;
  const now = hist[hist.length - 1].t;
  const win = hist.filter((s) => now - s.t <= 1500);
  if (win.length < 5 || (now - win[0].t) < 1500) return null;
  for (const s of win) if (!(s.level > 0.75 && s.tr > 0.5)) return null;
  return { durMs: now - win[0].t };
}
function panicWordRe(word) {
  const esc = String(word || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp("\\b" + esc + "\\b", "i");
}
function panicWordFired(hits, nowMs) {
  // hits: [ms timestamps] — fires when the panic word lands 2x within 6s.
  return hits.filter((t) => nowMs - t <= 6000).length >= 2;
}
function panicCanArm(earOpenMs, nowMs) {
  return (nowMs - earOpenMs) > 10000; // ears must be open >10s before arming
}
function panicCooldownOk(lastPanicMs, nowMs) {
  return (nowMs - lastPanicMs) >= 60000; // max 1 panic alert / 60s
}
/* 5s cancel countdown as a pure state machine (the UI drives it with timers). */
function panicMachineNew() { return { state: "idle", endsAt: 0 }; }
function panicMachineStart(m, nowMs) { m.state = "countdown"; m.endsAt = nowMs + 5000; }
function panicMachineCancel(m) { m.state = "idle"; m.endsAt = 0; }
function panicMachineExpired(m, nowMs) {
  return m.state === "countdown" && nowMs >= m.endsAt;
}
