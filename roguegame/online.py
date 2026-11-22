"""Talking to the online backend (a free Supabase project) without ever freezing the game.

Every call returns a Request at once; the game checks `req.done` each frame.
  Browser (pygbag): the page's own fetch(), via a tiny JavaScript helper.
  Desktop: urllib in a background thread.
With no assets/online.json (or an empty one) everything is offline and the Arena uses AI ghosts.

assets/online.json:  {"url": "https://YOUR-PROJECT.supabase.co", "key": "YOUR-ANON-PUBLIC-KEY"}
The anon key is meant to be public; the database rules (tools/supabase_setup.sql) only let
players add and read ghosts and scores - never change or delete them.
"""
import json
import os
import sys
import threading
import urllib.parse

from . import storage

WEB = sys.platform == "emscripten"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT = 8.0

_config = None
_counter = 0

_JS = r"""
window.srResults = window.srResults || {};
window.srFetch = function (id, method, url, headers, body) {
  const opts = {method: method, headers: JSON.parse(headers)};
  if (body) opts.body = body;
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 8000);
  opts.signal = ctl.signal;
  fetch(url, opts)
    .then(r => r.text().then(t => { window.srResults[id] = JSON.stringify({status: r.status, text: t}); }))
    .catch(e => { window.srResults[id] = JSON.stringify({status: 0, text: String(e)}); })
    .finally(() => clearTimeout(timer));
  return "";
};
window.srTake = function (id) {
  const v = window.srResults[id];
  if (v === undefined) return "";
  delete window.srResults[id];
  return v;
};
"""
_js_ready = False


def config():
    global _config
    if _config is None:
        _config = {}
        try:
            with open(os.path.join(ROOT, "assets", "online.json"), encoding="utf-8") as f:
                c = json.load(f)
            url = c.get("url", "")
            local = url.startswith(("http://localhost", "http://127.0.0.1"))     # testing on your own PC
            if (url.startswith("https://") or local) and c.get("key"):
                _config = dict(url=c["url"].rstrip("/"), key=c["key"])
        except (OSError, ValueError, AttributeError):
            pass
    return _config


def enabled():
    return bool(config())


class Request:
    def __init__(self, rid):
        self.id = rid
        self._done = False
        self.status = 0
        self.text = ""
        self.started = _now()

    def _finish(self, status, text):
        self.status, self.text, self._done = status, text, True

    @property
    def done(self):
        if not self._done and WEB:
            try:
                import platform as _p
                v = str(_p.window.srTake(self.id) or "")
                if v:
                    d = json.loads(v)
                    self._finish(int(d["status"]), d["text"])
            except Exception as e:      # noqa: BLE001
                self._finish(0, repr(e))
        if not self._done and _now() - self.started > TIMEOUT + 2:
            self._finish(0, "timed out")
        return self._done

    @property
    def ok(self):
        return self.done and 200 <= self.status < 300

    def json(self, default=None):
        try:
            return json.loads(self.text) if self.text else default
        except ValueError:
            return default


def _now():
    import time
    return time.time()


def _offline():
    r = Request("offline")
    r._finish(0, "offline")
    return r


def request(method, path, query=None, body=None, extra_headers=None):
    """Start an HTTP request to the backend. Returns a Request immediately."""
    global _counter, _js_ready
    c = config()
    if not c:
        return _offline()
    _counter += 1
    url = f"{c['url']}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query, safe=",.*()")
    headers = {"apikey": c["key"], "Authorization": f"Bearer {c['key']}", "Content-Type": "application/json"}
    headers.update(extra_headers or {})
    data = json.dumps(body) if body is not None else ""
    req = Request(f"r{_counter}")
    if WEB:
        try:
            import platform as _p
            if not _js_ready:
                _p.window.eval(_JS)
                _js_ready = True
            _p.window.srFetch(req.id, method, url, json.dumps(headers), data)
        except Exception as e:          # noqa: BLE001
            req._finish(0, repr(e))
        return req

    def work():
        import urllib.request
        import urllib.error
        try:
            rq = urllib.request.Request(url, data=data.encode() if data else None, headers=headers, method=method)
            with urllib.request.urlopen(rq, timeout=TIMEOUT) as resp:
                req._finish(resp.status, resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            req._finish(e.code, e.read().decode("utf-8", "replace"))
        except Exception as e:          # noqa: BLE001
            req._finish(0, repr(e))
    threading.Thread(target=work, daemon=True).start()
    return req


# ---------------------------------------------------------------- the game's calls
def upload_ghost(rec):
    return request("POST", "/rest/v1/ghosts", body=rec, extra_headers={"Prefer": "return=minimal"})


def find_ghosts(rnd, version, my_id):
    return request("GET", "/rest/v1/ghosts", query={
        "select": "player,name,cls,round,wins,losses,version,build",
        "round": f"eq.{rnd}", "version": f"eq.{version}", "player": f"neq.{my_id}",
        "order": "created_at.desc", "limit": "40"})


def submit_score(rec):
    return request("POST", "/rest/v1/scores", body=rec, extra_headers={"Prefer": "return=minimal"})


def top_scores(version, n=12):
    return request("GET", "/rest/v1/scores", query={
        "select": "name,cls,wins,hearts,version,created_at", "version": f"eq.{version}",
        "order": "wins.desc,hearts.desc,created_at.asc", "limit": str(n)})


# ---------------------------------------------------------------- player profile (this browser / PC)
def profile():
    try:
        p = json.loads(storage.read("profile") or "{}")
    except ValueError:
        p = {}
    if not p.get("id"):
        import random
        rng = random.SystemRandom() if hasattr(random, "SystemRandom") else random.Random()
        p = dict(id="%016x" % rng.getrandbits(64), name=f"Ronin-{rng.randrange(1000, 10000)}")
        storage.write("profile", json.dumps(p))
    return p


def clean_name(name):
    keep = "".join(ch for ch in name if ch.isalnum() or ch in " -_.'")
    return " ".join(keep.split())[:14]


def set_name(name):
    p = profile()
    n = clean_name(name)
    if n:
        p["name"] = n
        storage.write("profile", json.dumps(p))
    return p


def best():
    try:
        return json.loads(storage.read("arena_best") or "null")
    except ValueError:
        return None


def record_best(rec):
    b = best()
    if not b or (rec["wins"], rec["hearts"]) > (b["wins"], b["hearts"]):
        storage.write("arena_best", json.dumps(rec))
        return True
    return False
