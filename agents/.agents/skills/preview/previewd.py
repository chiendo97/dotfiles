#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["markdown>=3.6", "pygments>=2.19"]
# ///
"""previewd — serve .md/.html files for local browser preview.

Usage:
  previewd.py serve            start server on 0.0.0.0:<random port>
  previewd.py upload FILE      copy file into served root, print its URL
"""

import argparse
import html as html_mod
import http.server
import os
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

STATE = Path.home() / ".previewd"
BM = Path(__file__).resolve().parent / "bm.bundle.js"   # bundled beautiful-mermaid (browser global `bm`)
ADDR, PID, LOG, FILES = (STATE / n for n in ("addr", "pid", "serve.log", "files"))
EXTS = (".md", ".markdown", ".html", ".htm")
PYG_LIGHT = HtmlFormatter(style="default").get_style_defs(".codehilite")
PYG_DARK = HtmlFormatter(style="one-dark").get_style_defs(".codehilite")
CSS = """
:root,:root[data-theme="light"]{color-scheme:light;--fg:#1f2328;--bg:#ffffff;--muted:#656d76;--border:#d0d7de;--code-bg:#f6f8fa;--accent:#0969da}
:root[data-theme="dark"]{color-scheme:dark;--fg:#e6edf3;--bg:#0d1117;--muted:#8b949e;--border:#30363d;--code-bg:#161b22;--accent:#58a6ff}
*{box-sizing:border-box}
body{max-width:860px;margin:0 auto;padding:2.5rem 1.5rem;color:var(--fg);background:var(--bg);
font:16px/1.65 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
h1,h2,h3,h4{line-height:1.25;margin:1.6em 0 .6em;font-weight:600}
h1{font-size:2em;border-bottom:1px solid var(--border);padding-bottom:.3em}
h2{font-size:1.5em;border-bottom:1px solid var(--border);padding-bottom:.3em}
h3{font-size:1.25em} h4{font-size:1em}
p{margin:.7em 0}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
code{font:.875em ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:var(--code-bg);
padding:.15em .4em;border-radius:6px}
pre{background:var(--code-bg);border:1px solid var(--border);border-radius:8px;padding:1em;
overflow-x:auto;line-height:1.45}
pre code{background:none;padding:0;font-size:.875em}
pre.mermaid,pre.mm{background:none;border:none;text-align:center;overflow-x:auto}
pre.mermaid svg,pre.mm svg{max-width:100%;height:auto;display:block;margin:0 auto}
pre.mm .node{filter:drop-shadow(0 3px 6px rgba(0,0,0,.18));transition:filter .2s}
pre.mm .node:hover{filter:drop-shadow(0 9px 18px rgba(0,0,0,.32))}
:root[data-theme="dark"] pre.mm .node{filter:drop-shadow(0 3px 8px rgba(0,0,0,.55))}
:root[data-theme="dark"] pre.mm .node:hover{filter:drop-shadow(0 9px 20px rgba(88,166,255,.5))}
pre.mm .node rect[stroke^="var("],pre.mm .node polygon[stroke^="var("]{stroke-width:1.5px}
.mm-theme{position:fixed;top:12px;right:12px;z-index:99;font:12px/1.4 system-ui,sans-serif;
color:var(--fg);background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:5px 8px;
cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.18)}
.mm-theme:hover{border-color:var(--accent)}
pre.mm .edge[stroke^="var("]{stroke-width:2px;stroke-dasharray:7 5;animation:mflow .7s linear infinite}
@keyframes mflow{to{stroke-dashoffset:-12}}
blockquote{margin:.8em 0;padding:.2em 1em;color:var(--muted);border-left:4px solid var(--border)}
table{border-collapse:collapse;display:block;overflow-x:auto;margin:.8em 0;max-width:100%}
th,td{border:1px solid var(--border);padding:.45em .9em}
th{background:var(--code-bg);font-weight:600}
tr:nth-child(2n) td{background:var(--code-bg)}
img{max-width:100%} hr{border:none;border-top:2px solid var(--border);margin:2em 0}
ul,ol{padding-left:2em} li{margin:.25em 0}
input[type=checkbox]{margin-right:.4em}
thead{display:table-header-group}
""" + PYG_LIGHT + "\n" + PYG_DARK.replace(".codehilite", ':root[data-theme="dark"] .codehilite')
MD = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "sane_lists", "codehilite",
                                   "attr_list", "md_in_html"],
                       extension_configs={"codehilite": {"guess_lang": False, "noclasses": False}})
# ```mermaid fences -> raw <pre class='mermaid'> blocks, drawn client-side from a CDN
MERMAID = re.compile(r"^(```)mermaid[ \t]*\n(.*?)^\1[ \t]*$", re.M | re.S)
MERMAID_JS_JS = """
(function () {
  var root = document.documentElement;
  var choice = root.dataset.themeChoice || 'auto';
  var system = matchMedia('(prefers-color-scheme: dark)');
  var bmBlocks = [], fallbackBlocks = [];
  var classic = null, fallbackRender = Promise.resolve();
  var blocks = [].slice.call(document.querySelectorAll('pre.mermaid'));
  blocks.forEach(function (pre) {
    pre.dataset.src = pre.textContent;
    try {
      pre.innerHTML = bm.renderMermaidSVG(pre.dataset.src,
        Object.assign({}, bm.THEMES['github-' + root.dataset.theme], { transparent: true }));
      pre.classList.remove('mermaid');          // shield from classic mermaid's auto-scan
      pre.classList.add('mm');
      bmBlocks.push(pre);
    } catch (e) {
      fallbackBlocks.push(pre);
    }
  });
  function renderFallback() {
    if (!classic) return;
    // Classic Mermaid has global config: serialize renders, using the latest theme.
    fallbackRender = fallbackRender.then(async function () {
      classic.initialize({ startOnLoad: false, theme: root.dataset.theme === 'dark' ? 'dark' : 'default' });
      fallbackBlocks.forEach(function (pre) {
        pre.removeAttribute('data-processed');
        pre.textContent = pre.dataset.src;
      });
      await classic.run({ nodes: fallbackBlocks });
    }).catch(function (e) { console.warn('Mermaid rendering failed', e); });
  }
  function applyTheme() {
    root.dataset.themeChoice = choice;
    root.dataset.theme = choice === 'auto' ? (system.matches ? 'dark' : 'light') : choice;
    bmBlocks.forEach(function (pre) {
      try {
        pre.innerHTML = bm.renderMermaidSVG(pre.dataset.src,
          Object.assign({}, bm.THEMES['github-' + root.dataset.theme], { transparent: true }));
      } catch (e) {}
    });
    renderFallback();
  }
  if (fallbackBlocks.length) {
    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js';
    s.onload = function () { classic = window.mermaid; renderFallback(); };
    document.head.appendChild(s);
  }
  var sel = document.createElement('select');
  sel.className = 'mm-theme';
  sel.title = 'Page theme';
  sel.setAttribute('aria-label', 'Page theme');
  ['auto', 'light', 'dark'].forEach(function (t) {
    var o = document.createElement('option');
    o.value = t; o.textContent = t.charAt(0).toUpperCase() + t.slice(1);
    o.selected = t === choice;
    sel.appendChild(o);
  });
  sel.onchange = function () {
    choice = sel.value;
    try { localStorage.setItem('previewd-theme', choice); } catch (e) {}
    applyTheme();
  };
  system.addEventListener('change', function () { if (choice === 'auto') applyTheme(); });
  document.body.appendChild(sel);
})();
"""
MERMAID_JS = ("<script src='/bm.bundle.js'></" + "script>\n"
              "<script>" + MERMAID_JS_JS + "</" + "script>")


def _mermaid_sub(m):
    src = m.group(2).strip()
    return f"<pre class='mermaid'>{html_mod.escape(src)}</" + "pre>\n"


def render_md(name: str, body: bytes) -> bytes:
    text = MERMAID.sub(_mermaid_sub, body.decode("utf-8", "replace"))
    MD.reset()
    html = MD.convert(text)
    extra = MERMAID_JS if "class='mermaid'" in html else "<script>" + MERMAID_JS_JS + "</script>"
    return (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<script>(function(){"
            "var choice='auto';try{var stored=localStorage.getItem('previewd-theme');"
            "if(['auto','light','dark'].indexOf(stored)!==-1)choice=stored;"
            "else if(stored!==null)localStorage.setItem('previewd-theme',choice);}catch(e){}"
            "var root=document.documentElement;root.dataset.themeChoice=choice;"
            "root.dataset.theme=choice==='auto'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):choice;"
            "})();</script>"
            f"<title>{name}</title><style>{CSS}</style></head><body>{html}{extra}</body></html>").encode()


def make_handler(root: str):
    root = os.path.abspath(root)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            name = os.path.basename(urllib.parse.unquote(self.path.lstrip("/")))
            if name == "bm.bundle.js":
                data = BM.read_bytes() if BM.is_file() else b""
                self._send(200 if BM.is_file() else 404, "application/javascript", data)
                return
            if name in ("", "index.html"):
                self._send(200, "text/html", f"<h1>previewd</h1><p>root: {root}</p>".encode())
                return
            path = os.path.abspath(os.path.join(root, name))
            if not path.startswith(root + os.sep) or not os.path.isfile(path):
                self._send(404, "text/plain", b"not found")
                return
            body = open(path, "rb").read()
            if name.endswith((".md", ".markdown")):
                self._send(200, "text/html", render_md(name, body))
            elif name.endswith((".html", ".htm")):
                self._send(200, "text/html", body)
            else:
                self._send(200, "text/plain", body)

        def _send(self, code: int, ctype: str, data: bytes):
            self.send_response(code)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    return Handler


def cmd_serve(a):
    root = Path(a.root)
    root.mkdir(parents=True, exist_ok=True)
    port = a.port
    if port == 0 and ADDR.exists():   # reuse previous port when free
        try:
            port = int(ADDR.read_text().strip().rsplit(":", 1)[-1])
        except ValueError:
            pass
    try:
        httpd = http.server.ThreadingHTTPServer((a.host, port), make_handler(str(root)))
    except OSError:
        if port:
            print(f"port {port} busy, picking a free one", flush=True)
        httpd = http.server.ThreadingHTTPServer((a.host, 0), make_handler(str(root)))
    host, port = httpd.server_address[:2]
    STATE.mkdir(parents=True, exist_ok=True)
    ADDR.write_text(f"{host}:{port}")
    PID.write_text(str(os.getpid()))
    print(f"previewd serving {root} at http://{host}:{port}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def cmd_upload(a):
    src = Path(a.file).expanduser()
    if not src.is_file():
        print(f"not a file: {src}", file=sys.stderr)
        return 1
    if src.suffix.lower() not in EXTS:
        print(f"unsupported type: {src.suffix} (allowed: {', '.join(EXTS)})", file=sys.stderr)
        return 1
    name = a.name or src.name
    if "/" in name or name.startswith("."):
        print("name must be a plain filename", file=sys.stderr)
        return 1
    FILES.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, FILES / name)
    if a.server:
        addr = a.server
    elif ADDR.exists():
        addr = ADDR.read_text().strip()
    else:
        print("no previewd server recorded yet; start one first (serve)", file=sys.stderr)
        return 1
    print(f"http://{addr}/{name}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="previewd", description="Serve md/html files for local preview")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="start the preview server on a random free port")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=0, help="0 = random free port")
    s.add_argument("--root", default=str(FILES), help="directory files are served from")
    s.set_defaults(fn=cmd_serve)

    u = sub.add_parser("upload", help="copy a .md or .html file into the served root, print its URL")
    u.add_argument("file")
    u.add_argument("--name", help="serve under this filename instead of the basename")
    u.add_argument("--server", help="host:port to print in the URL (overrides the recorded address)")
    u.set_defaults(fn=cmd_upload)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())