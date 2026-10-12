// Panic-mode detector unit tests. Run: node tests/panic-test.js
// Extracts the pure functions between PANIC-START / PANIC-END in dashboard/app.js.
const fs = require("fs");
const path = require("path");
const src = fs.readFileSync(
  path.join(__dirname, "..", "dashboard", "app.js"), "utf8");
const startMark = "/* PANIC-START";
const endMark = "/* PANIC-END";
let block = src.split(startMark)[1].split(endMark)[0];
block = block.slice(block.indexOf("\n") + 1); // drop the marker comment's tail
eval(block);

let pass = 0, fail = 0;
const ok = (name, cond) => { cond ? pass++ : (fail++, console.log("FAIL:", name)); };

// treble ratio
ok("tr basic", Math.abs(panicTrebleRatio({ bass: 0.1, mid: 0.2, treble: 0.7 }) - 0.7) < 1e-6);
ok("tr zeros", panicTrebleRatio({}) === 0);

// scream detector
const mk = (n, level, tr, step = 100) => {
  const h = []; for (let i = 0; i < n; i++) h.push({ t: i * step, level, tr }); return h;
};
ok("scream fires on sustained loud high-pitch", !!detectScream(mk(17, 0.9, 0.7)));
ok("scream ignores short clap", !detectScream([
  { t: 0, level: 0.2, tr: 0.3 }, { t: 100, level: 0.2, tr: 0.3 },
  { t: 200, level: 0.95, tr: 0.8 }, { t: 300, level: 0.2, tr: 0.3 },
  { t: 400, level: 0.2, tr: 0.3 }, { t: 500, level: 0.2, tr: 0.3 }]));
ok("scream ignores laughter-like", !detectScream(mk(17, 0.5, 0.3)));
ok("scream ignores loud bass-dominant", !detectScream(mk(17, 0.9, 0.2)));
ok("scream ignores 1s burst (not sustained)", !detectScream(mk(11, 0.9, 0.7)));
ok("scream safe on short history", !detectScream([{ t: 0, level: 0.9, tr: 0.8 }]));
ok("scream safe on empty history", !detectScream([]));
ok("scream ignores interrupted sustain", !(() => {
  const h = mk(17, 0.9, 0.7); h[8].level = 0.3; return detectScream(h);
})());

// panic word
const re = panicWordRe("help");
ok("word matches case-insensitive", re.test("HELP me") && re.test("help!"));
ok("word respects boundaries", !re.test("helper") && !re.test("shelf"));
ok("word escapes regex chars", panicWordRe("a+b").test("say a+b now") &&
  !panicWordRe("a+b").test("say aab now"));
ok("word fires on 2x in 6s", panicWordFired([1000, 3000], 4000));
ok("word silent on 1x", !panicWordFired([1000], 4000));
ok("word silent when spread out", !panicWordFired([1000, 12000], 13000));
ok("word ignores stale hits", !panicWordFired([1000, 2000], 20000));

// arming + cooldown
ok("arms after ears open >10s", panicCanArm(0, 11001));
ok("no arm before 10s", !panicCanArm(0, 5000));
ok("cooldown ok after 60s", panicCooldownOk(0, 61000));
ok("cooldown blocks before 60s", !panicCooldownOk(0, 30000));

// cancel countdown state machine
const m = panicMachineNew();
ok("machine starts idle", m.state === "idle" && !panicMachineExpired(m, 99999));
panicMachineStart(m, 1000);
ok("machine counts down", m.state === "countdown" && !panicMachineExpired(m, 5999));
ok("machine expires at 5s", panicMachineExpired(m, 6000));
panicMachineCancel(m);
ok("cancel prevents the alert", m.state === "idle" && !panicMachineExpired(m, 99999));

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
