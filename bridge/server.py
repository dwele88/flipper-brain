"""NeuroFlipper bridge: HTTP API between the Flipper Zero (USB serial CLI)
and the dashboard / playground. Serves the dashboard static files too.

Run:  python -m bridge.server [--config config.yaml]
Then open the printed URL.
"""
from __future__ import annotations

import argparse
import os
import sys
import threading

from flask import Flask, jsonify, request, send_from_directory, Response

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge.flipper import FlipperConnection, FlipperError  # noqa: E402
from playground.engine import Playground  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(REPO_ROOT, "dashboard")

DEFAULTS = {
    "serial": {"port": "/dev/ttyACM0", "baud": 230400},
    "server": {"host": "127.0.0.1", "port": 8787},
    "playground": {
        "default_interval": 20,
        "game_allowlist": [],
        "app_tour_allowlist": [],
    },
}


def load_config(path: str) -> dict:
    cfg = {k: dict(v) for k, v in DEFAULTS.items()}
    if os.path.exists(path):
        if yaml is None:
            raise RuntimeError("pyyaml is required to read config.yaml (pip install -r requirements.txt)")
        try:
            with open(path) as fh:
                user = yaml.safe_load(fh) or {}
        except yaml.YAMLError as exc:
            print(f"WARNING: ignoring malformed config {path} ({exc}); using defaults",
                  file=sys.stderr)
            return cfg
        for section, values in user.items():
            if section in cfg and isinstance(values, dict):
                cfg[section].update(values)
            else:
                cfg[section] = values
    return cfg


def create_app(config: dict) -> Flask:
    app = Flask(__name__)
    try:
        baud = int(config["serial"].get("baud", 230400))
    except (TypeError, ValueError):
        print(f"WARNING: invalid baud {config['serial'].get('baud')!r}; using 230400",
              file=sys.stderr)
        baud = 230400
    flipper = FlipperConnection(config["serial"]["port"], baud)
    pg = Playground(flipper, config.get("playground", {}))

    def _require_ext(path: str) -> str:
        """Confine all file operations to /ext (SD card). Never /int."""
        p = (path or "").strip()
        if p != "/ext" and not p.startswith("/ext/"):
            raise ValueError("path must be under /ext (SD card)")
        if ".." in p.split("/"):
            raise ValueError("invalid path")
        if "%2e" in p.lower() or "%2f" in p.lower():
            raise ValueError("encoded path segments are not allowed")
        return p

    # -- dashboard static -------------------------------------------------
    @app.route("/")
    def index():
        return send_from_directory(DASHBOARD_DIR, "index.html")

    @app.route("/<path:filename>")
    def static_files(filename: str):
        return send_from_directory(DASHBOARD_DIR, filename)

    # -- device -----------------------------------------------------------
    @app.route("/api/status")
    def status():
        connected = flipper.is_connected() or flipper.connect()
        return jsonify({
            "connected": connected,
            "port": flipper.port,
            "baud": flipper.baud,
            "last_error": flipper.last_error,
            "playground": pg.status(),
        })

    @app.route("/api/device")
    def device():
        try:
            return jsonify({"ok": True, "info": flipper.device_info()})
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/cli", methods=["POST"])
    def cli():
        body = request.get_json(force=True, silent=True) or {}
        command = (body.get("command") or "").strip()
        if not command:
            return jsonify({"ok": False, "error": "command is required"}), 400
        if command.startswith("start_rpc_session"):
            return jsonify({"ok": False, "error": "RPC mode is not supported by the bridge"}), 400
        try:
            timeout = float(body.get("timeout", 15))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "timeout must be a number"}), 400
        if not (0 < timeout <= 120):
            return jsonify({"ok": False, "error": "timeout must be between 0 and 120 seconds"}), 400
        stop_after = body.get("stop_after")
        if stop_after is not None:
            try:
                stop_after = float(stop_after)
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "stop_after must be a number"}), 400
            if not (0 < stop_after <= 120):
                return jsonify({"ok": False, "error": "stop_after must be between 0 and 120 seconds"}), 400
        try:
            out = flipper.send(command, timeout=timeout, stop_after=stop_after)
            return jsonify({"ok": True, "output": out})
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/reboot", methods=["POST"])
    def reboot():
        try:
            return jsonify({"ok": True, "output": flipper.reboot()})
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/screen")
    def screen():
        # Stock CLI exposes no framebuffer/screenshot command; documented as planned.
        return jsonify({
            "ok": False,
            "error": "screen capture is not available via the stock CLI "
                     "(no screenshot command exists) — planned, needs on-device verification",
        }), 501

    # -- files -------------------------------------------------------------
    @app.route("/api/files")
    def files():
        try:
            path = _require_ext(request.args.get("path", "/ext"))
            return jsonify({"ok": True, "path": path, "listing": flipper.storage_list(path)})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/file")
    def file_read():
        raw = request.args.get("path", "")
        if not raw:
            return jsonify({"ok": False, "error": "path is required"}), 400
        try:
            path = _require_ext(raw)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        try:
            return jsonify({"ok": True, "path": path, "content": flipper.storage_read(path)})
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/file", methods=["POST"])
    def file_write():
        body = request.get_json(force=True, silent=True) or {}
        raw = body.get("path", "")
        if not raw:
            return jsonify({"ok": False, "error": "path is required"}), 400
        try:
            path = _require_ext(raw)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        content = body.get("content", "")
        try:
            return jsonify({"ok": True, "output": flipper.storage_write(path, content)})
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/file", methods=["DELETE"])
    def file_delete():
        body = request.get_json(force=True, silent=True) or {}
        raw = body.get("path", "")
        if not raw:
            return jsonify({"ok": False, "error": "path is required"}), 400
        try:
            path = _require_ext(raw)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        try:
            return jsonify({"ok": True, "output": flipper.storage_remove(path)})
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/mkdir", methods=["POST"])
    def mkdir():
        body = request.get_json(force=True, silent=True) or {}
        raw = body.get("path", "")
        if not raw:
            return jsonify({"ok": False, "error": "path is required"}), 400
        try:
            path = _require_ext(raw)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        try:
            return jsonify({"ok": True, "output": flipper.storage_mkdir(path)})
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    # -- apps --------------------------------------------------------------
    @app.route("/api/apps")
    def apps():
        try:
            return jsonify({"ok": True, "apps": flipper.loader_list()})
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/apps/launch", methods=["POST"])
    def app_launch():
        body = request.get_json(force=True, silent=True) or {}
        name = (body.get("name") or "").strip()
        if not name:
            return jsonify({"ok": False, "error": "name is required"}), 400
        try:
            return jsonify({"ok": True, "output": flipper.loader_open(name)})
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/apps/close", methods=["POST"])
    def app_close():
        try:
            return jsonify({"ok": True, "output": flipper.loader_close()})
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    # -- library (UberGuidoZ/Flipper file collection) -------------------------
    @app.route("/api/library/categories")
    def lib_categories():
        from bridge import library as lib
        return jsonify({"ok": True, "repo": lib.REPO_URL,
                        "categories": lib.categories()})

    @app.route("/api/library/browse")
    def lib_browse():
        from bridge import library as lib
        category = request.args.get("category", "")
        subpath = request.args.get("path", "")
        try:
            return jsonify({"ok": True, "category": category,
                            "files": lib.list_category(category, subpath)})
        except lib.LibraryError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/library/search")
    def lib_search():
        from bridge import library as lib
        q = request.args.get("q", "")
        if not q:
            return jsonify({"ok": False, "error": "q is required"}), 400
        try:
            return jsonify({"ok": True, "results": lib.search(q)})
        except lib.LibraryError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/library/install", methods=["POST"])
    def lib_install():
        from bridge import library as lib
        body = request.get_json(force=True, silent=True) or {}
        repo_path = (body.get("repo_path") or "").strip().lstrip("/")
        if not repo_path:
            return jsonify({"ok": False, "error": "repo_path is required"}), 400
        try:
            return jsonify({"ok": True, **lib.install(flipper, repo_path)})
        except lib.LibraryError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/library/installed")
    def lib_installed():
        from bridge import library as lib
        category = request.args.get("category", "")
        if category not in lib.CATEGORIES:
            return jsonify({"ok": False, "error": "unknown category"}), 400
        sd_dir, installable, _ = lib.CATEGORIES[category]
        if not installable or not sd_dir:
            return jsonify({"ok": True, "installed": [],
                            "note": "browse-only category"})
        try:
            return jsonify({"ok": True, "sd_path": sd_dir,
                            "installed": flipper.storage_list(sd_dir)})
        except FlipperError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    # -- playground ---------------------------------------------------------
    @app.route("/api/playground/moods")
    def moods():
        return jsonify({"ok": True, "moods": pg.describe_moods()})

    @app.route("/api/playground/start", methods=["POST"])
    def pg_start():
        body = request.get_json(force=True, silent=True) or {}
        mood = (body.get("mood") or "").strip()
        try:
            interval = int(body.get("interval", config["playground"]["default_interval"]))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "interval must be an integer"}), 400
        try:
            pg.start(mood, interval)
            return jsonify({"ok": True, "status": pg.status()})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.route("/api/playground/stop", methods=["POST"])
    def pg_stop():
        pg.stop()
        return jsonify({"ok": True, "status": pg.status()})

    @app.route("/api/playground/status")
    def pg_status():
        return jsonify({"ok": True, "status": pg.status()})

    @app.route("/api/playground/thoughts")
    def pg_thoughts():
        try:
            since = int(request.args.get("since", 0))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "since must be an integer"}), 400
        thoughts, cursor = pg.thoughts_since(since)
        return jsonify({"ok": True, "thoughts": thoughts, "cursor": cursor})

    @app.route("/api/playground/stream")
    def pg_stream():
        def gen():
            cursor = 0
            while True:
                thoughts, cursor = pg.thoughts_since(cursor)
                for t in thoughts:
                    import json as _json
                    yield f"data: {_json.dumps(t)}\n\n"
                import time as _time
                _time.sleep(1)
        return Response(gen(), mimetype="text/event-stream")

    # -- eyes (phone camera as the Flipper's vision) --------------------------
    @app.route("/api/eyes/frame", methods=["POST"])
    def eyes_frame():
        import base64
        import binascii
        import datetime as _dt
        from bridge.vision import analyze_frame, scene_signature
        body = request.get_json(force=True, silent=True) or {}
        try:
            w, h = int(body.get("w", 0)), int(body.get("h", 0))
            px = base64.b64decode(body.get("px", ""), validate=True)
        except (TypeError, ValueError, binascii.Error):
            return jsonify({"ok": False, "error": "px must be base64 bytes"}), 400
        try:
            prev_raw = eyes_frame._prev
            prev = prev_raw[0] if prev_raw and prev_raw[1] == (w, h) else None
            brightness, motion, zones = analyze_frame(px, w, h, prev)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        eyes_frame._prev = (px, (w, h))
        signature = scene_signature(
            brightness, motion, zones, _dt.datetime.now().hour)
        try:
            ts = float(body.get("t") or __import__("time").time())
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "t must be a number"}), 400
        sample = {"ts": ts,
                  "brightness": brightness, "motion": motion, "zones": zones,
                  "signature": signature}
        pg.set_external("vision", sample)
        return jsonify({"ok": True, **sample})
    eyes_frame._prev = None  # in-memory only: previous frame for motion

    # -- ears (phone mic as the Flipper's hearing) ----------------------------
    def _ts(raw, default: float) -> float:
        try:
            return float(raw if raw is not None else default)
        except (TypeError, ValueError):
            raise ValueError("t must be a number")

    @app.route("/api/ears", methods=["POST"])
    def ears():
        import time as _time
        body = request.get_json(force=True, silent=True) or {}

        def _f(key: str) -> float:
            try:
                return max(0.0, min(1.0, float(body.get(key, 0.0))))
            except (TypeError, ValueError):
                return 0.0

        try:
            ts = _ts(body.get("t"), _time.time())
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        sample = {"ts": ts,
                  "level": _f("level"), "bass": _f("bass"),
                  "mid": _f("mid"), "treble": _f("treble")}
        pg.set_external("hearing", sample)
        return jsonify({"ok": True, **sample})

    # -- voice (talk to the brain) --------------------------------------------
    @app.route("/api/voice", methods=["POST"])
    def voice():
        from bridge import voice as voice_mod
        from playground.sense import parse_battery
        body = request.get_json(force=True, silent=True) or {}
        text = (body.get("text") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "text is required"}), 400
        ext = pg.external_snapshot()
        battery = None
        reachable = False
        try:
            battery = parse_battery(flipper.send("info power", timeout=5))
            reachable = True
        except FlipperError:
            pass

        def _lib_search(q: str):
            from bridge import library as lib
            return lib.search(q)

        ctx = {"mood": pg.status().get("mood"), "vision": ext["vision"],
               "hearing": ext["hearing"], "battery": battery,
               "reachable": reachable, "library_search": _lib_search}
        try:
            result = voice_mod.interpret(text, ctx)
        except Exception as exc:
            return jsonify({"ok": False, "error": f"voice failed: {exc}"}), 500
        action = result.get("action") or {}
        atype = action.get("type")
        try:
            if atype == "mood":
                pg.set_mood(action["mood"])
            elif atype == "trigger":
                pg.trigger()
            elif atype == "stop":
                pg.stop()
        except (ValueError, RuntimeError, KeyError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        # The user engaged — tag recent loud moments in hearing memory.
        try:
            pg.hearing_memory.note_engagement()
        except Exception:
            pass
        return jsonify({"ok": True, "reply": result["reply"],
                        "action": action or None})

    # -- raw input injection (UNVERIFIED — honest 501) -------------------------
    @app.route("/api/input", methods=["POST"])
    def raw_input():
        # The stock Flipper CLI exposes no documented button-press command
        # (no `input` command exists on stock/Momentum/Unleashed as of 2026).
        # Faking success would lie to the dashboard, so this stays 501 until
        # someone verifies a real injection path on actual hardware.
        body = request.get_json(force=True, silent=True) or {}
        key = (body.get("key") or "").strip()
        if key not in ("up", "down", "left", "right", "ok", "back"):
            return jsonify({"ok": False,
                            "error": "key must be one of up/down/left/right/ok/back"}), 400
        return jsonify({
            "ok": False,
            "error": "input injection unverified on this firmware — the stock "
                     "Flipper CLI has no button-press command. Not faked.",
        }), 501

    # -- brain remote control (always works — no Flipper needed) ---------------
    @app.route("/api/brain", methods=["POST"])
    def brain():
        body = request.get_json(force=True, silent=True) or {}
        action = (body.get("action") or "").strip()
        try:
            if action == "mood":
                mood = (body.get("mood") or "").strip()
                return jsonify({"ok": True, "status": pg.set_mood(mood)})
            if action == "trigger":
                return jsonify({"ok": True, "status": pg.trigger()})
            if action == "speak":
                text = (body.get("text") or "").strip()
                pg.speak(text, body.get("event") or "happy")
                return jsonify({"ok": True})
            return jsonify({"ok": False,
                            "error": "action must be mood|trigger|speak"}), 400
        except (ValueError, RuntimeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="NeuroFlipper bridge")
    parser.add_argument("--config", default=os.path.join(REPO_ROOT, "config.yaml"),
                        help="path to config.yaml")
    args = parser.parse_args()
    config = load_config(args.config)
    app = create_app(config)
    host, port = config["server"]["host"], int(config["server"]["port"])
    print(f"NeuroFlipper bridge on http://{host}:{port} "
          f"(serial: {config['serial']['port']})")
    # threaded=True so SSE + API can coexist
    app.run(host=host, port=port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    threading.current_thread().name = "main"
    main()
