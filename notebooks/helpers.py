"""How the notebooks show what they do: every API call as a card, lists as tables.

show(response) renders a requests.Response: the method and route, which agent
answered and in which role, the HTTP status and how long it took, the state
of the negotiation or transfer, the fields worth reading (PIDs, ids, the
agreement, the dataplane address) and both bodies, request and response.

Long values (DIDs, tokens) are shortened on screen only; the variables keep
them in full. Each output carries a plain-text version too, for nbconvert and
anything that does not render HTML.
"""

import html
import json
import re
from urllib.parse import urlsplit

from IPython.display import display

# Base URL -> how to call it on screen. 01_auth fills it in.
AGENTS = {}

LONG = 90
GOOD = {"FINALIZED", "AGREED", "VERIFIED", "ACCEPTED", "STARTED", "COMPLETED", "APPROVED"}
BAD = {"TERMINATED", "ERROR"}
WARN = {"SUSPENDED", "PENDING"}

# Fields worth a line of their own, wherever the answer puts them.
FIELDS = (
    "@type", "state", "consumerPid", "providerPid", "agreementId", "participant_id", "nick",
    "id", "name", "version", "dctTitle", "title", "dctFormat", "entity", "code", "reason",
)
NESTED = ("response", "negotiationAgentModel", "transferAgentModel", "error")

# The docs' palette (docs/app/global.css): mist paper and indigo ink in light,
# night indigo with sky and violet in dark; Geist and Geist Mono. Every style
# is inline with a light fallback, so a card still reads where Jupyter strips
# <style> (untrusted notebooks); THEME only switches the variables.
THEME = """<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap');
.eu {
  --eu-fg: hsl(242, 37%, 15%); --eu-muted: hsl(240, 12%, 40%); --eu-card: hsl(0, 0%, 100%);
  --eu-soft: hsl(220, 33%, 96%); --eu-border: hsla(240, 25%, 50%, .18); --eu-primary: hsl(252, 85%, 58%);
  --eu-accent: hsl(252, 80%, 95%); --eu-accent-fg: hsl(252, 70%, 35%);
  --eu-good: hsl(152, 65%, 32%); --eu-bad: hsl(354, 70%, 48%); --eu-warn: hsl(32, 90%, 40%);
  --eu-json-key: hsl(252, 60%, 45%); --eu-json-str: hsl(198, 80%, 30%); --eu-json-num: hsl(305, 55%, 42%);
  --eu-json-lit: hsl(240, 12%, 50%);
}
body[data-jp-theme-light="false"] .eu, body.vscode-dark .eu, body.vscode-high-contrast .eu {
  --eu-fg: hsl(210, 40%, 94%); --eu-muted: hsl(220, 20%, 68%); --eu-card: hsl(242, 40%, 9%);
  --eu-soft: hsl(242, 35%, 12%); --eu-border: hsla(220, 60%, 80%, .12); --eu-primary: hsl(200, 75%, 78%);
  --eu-accent: hsla(252, 70%, 60%, .16); --eu-accent-fg: hsl(252, 100%, 88%);
  --eu-good: hsl(152, 55%, 62%); --eu-bad: hsl(354, 85%, 72%); --eu-warn: hsl(38, 90%, 65%);
  --eu-json-key: hsl(252, 100%, 85%); --eu-json-str: hsl(200, 75%, 78%); --eu-json-num: hsl(300, 75%, 80%);
  --eu-json-lit: hsl(220, 20%, 62%);
}
.eu details > summary { list-style: none; }
.eu details > summary::-webkit-details-marker { display: none; }
.eu details > summary::before { content: "›"; display: inline-block; width: 1em; transition: transform .15s; }
.eu details[open] > summary::before { transform: rotate(90deg); }
.eu tr.eu-row:hover td { background: var(--eu-soft) !important; }
.eu tr { background: transparent !important; }
</style>"""


def v(name, fallback):
    return f"var(--eu-{name},{fallback})"


FG = v("fg", "#1f1d3d")
MUTED_FG = v("muted", "#5b5b72")
SOFT = v("soft", "#f2f5f9")
BORDER = v("border", "rgba(96,96,160,.18)")
PRIMARY = v("primary", "#6d4dff")
SANS = "Geist,var(--jp-ui-font-family),ui-sans-serif,system-ui,sans-serif"
MONO = "'Geist Mono',var(--jp-code-font-family),ui-monospace,SFMono-Regular,Menlo,monospace"
TONES = {
    "good": v("good", "#0f7a4d"), "bad": v("bad", "#d0293b"), "warn": v("warn", "#c2620a"),
    "info": PRIMARY, "plain": MUTED_FG,
}

CARD = (
    f"position:relative;overflow:hidden;border:1px solid {BORDER};border-radius:12px;"
    f"padding:14px 16px 12px;margin:8px 0;background:{v('card', '#fff')};color:{FG};"
    f"font-family:{SANS};font-size:13px;line-height:1.55;"
    "box-shadow:0 1px 2px rgba(36,35,76,.04),0 4px 16px -8px rgba(36,35,76,.12)"
)
# The brand gradient of the docs, sky to violet to magenta, as a hairline on top.
STRIPE = (
    '<div style="position:absolute;top:0;left:0;right:0;height:2px;'
    'background:linear-gradient(100deg,#9dd5f2 0%,#8b6cff 50%,#e86cf0 100%)"></div>'
)
TITLE = f"font-weight:600;font-size:14px;letter-spacing:-.01em;margin-bottom:6px;color:{FG}"
PRE = (
    f"margin:6px 0 0;padding:10px 12px;border-radius:8px;background:{SOFT};border:1px solid {BORDER};"
    f"color:{FG};font-family:{MONO};font-size:12px;line-height:1.55;white-space:pre;overflow:auto;max-height:340px"
)
MUTED = f"color:{MUTED_FG}"
# Jupyter styles output tables (right-aligned, striped); these win over it.
CELL = f"text-align:left;background:transparent;border:none;color:{FG};"
ROW = "background:transparent"
JSON_COLORS = {
    "key": v("json-key", "#4b32c3"), "str": v("json-str", "#0e6a8a"),
    "num": v("json-num", "#a8329a"), "lit": v("json-lit", "#6b6b85"),
}
JSON_TOKEN = re.compile(
    r"(?P<str>&quot;(?:\\.|[^\\&]|&(?!quot;))*&quot;)(?P<colon>\s*:)?"
    r"|(?P<lit>\b(?:true|false|null)\b)"
    r"|(?P<num>-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)"
)


def short(value, keep=LONG):
    if isinstance(value, str) and len(value) > keep:
        tail = min(12, keep // 3)
        return f"{value[:keep - tail - 1]}…{value[-tail:]}"
    return value


def _shorten(node):
    if isinstance(node, dict):
        return {k: _shorten(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_shorten(v) for v in node]
    return short(node)


def _json(body):
    return json.dumps(_shorten(body), indent=2, ensure_ascii=False)


def _badge(text, tone="info"):
    c = TONES[tone]
    return (
        f'<span style="display:inline-block;padding:1px 8px;border-radius:999px;font-family:{MONO};font-size:11px;'
        f'font-weight:500;letter-spacing:.02em;color:{c};border:1px solid {c};'
        f'background:color-mix(in srgb,{c} 10%,transparent)">{html.escape(str(text))}</span>'
    )


def _method(name):
    return (
        f'<span style="display:inline-block;padding:1px 7px;border-radius:6px;font-family:{MONO};font-size:11px;'
        f'font-weight:600;color:{v("accent-fg", "#3b2a9e")};background:{v("accent", "#efebfe")}">{html.escape(name)}</span>'
    )


def _card(inner):
    return f'{THEME}<div class="eu" style="{CARD}">{STRIPE}{inner}</div>'


def _tone(state):
    s = str(state).rsplit(":", 1)[-1].upper()
    return "good" if s in GOOD else "bad" if s in BAD else "warn" if s in WARN else "info"


def _who(url):
    # The longest match wins: the dataplane URL starts with the provider's.
    matches = [base for base in AGENTS if url.startswith(base)]
    return AGENTS[max(matches, key=len)] if matches else urlsplit(url).netloc


def state_of(body):
    """The state of a negotiation or transfer, wherever the answer puts it."""
    if not isinstance(body, dict):
        return None
    for key in ("response", "negotiationAgentModel", "transferAgentModel"):
        if isinstance(body.get(key), dict) and body[key].get("state"):
            return body[key]["state"]
    return body.get("state")


def find_dataplane(node):
    """The dataplane URL in a transfer start answer, wherever it is nested."""
    if isinstance(node, dict):
        node = list(node.values())
    if isinstance(node, list):
        for value in node:
            found = value if isinstance(value, str) and "dataplane" in value else find_dataplane(value)
            if found:
                return found
    return None


def highlights(body):
    """(field, value) pairs worth reading at a glance."""
    if isinstance(body, list):
        return [("items", len(body))]
    if not isinstance(body, dict):
        return []
    out, seen = [], set()
    for scope in (body, *(body.get(k) for k in NESTED)):
        if not isinstance(scope, dict):
            continue
        for key in FIELDS:
            value = scope.get(key)
            if value in (None, "", []) or key in seen or isinstance(value, (dict, list)) and key != "reason":
                continue
            seen.add(key)
            out.append((key, value if key != "reason" else " ".join(map(str, value))[:300]))
    agreement = ((body.get("negotiationAgentModel") or {}).get("agreement") or {}).get("id")
    if agreement:
        out.append(("agreement", agreement))
    dataplane = find_dataplane(body)
    if dataplane:
        out.append(("dataplane", dataplane))
    error = body.get("error")
    if isinstance(error, dict):
        out.append(("error", "the agent answered with a DSP error"))
    elif error:
        out.append(("error", error))
    return out


def _parse(raw):
    if raw is None or raw == b"" or raw == "":
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def _colored(text):
    """JSON with the docs' colours: violet keys, sky strings, magenta numbers."""
    def paint(m):
        if m.group("str"):
            kind = "key" if m.group("colon") else "str"
            return f'<span style="color:{JSON_COLORS[kind]}">{m.group("str")}</span>{m.group("colon") or ""}'
        kind = "lit" if m.group("lit") else "num"
        return f'<span style="color:{JSON_COLORS[kind]}">{m.group(0)}</span>'

    return JSON_TOKEN.sub(paint, html.escape(text, quote=True))


def _short_body(body):
    return (body if isinstance(body, str) else _json(body)).count("\n") < 30


def _details(label, body, open_):
    text = body if isinstance(body, str) else _json(body)
    lines = text.count("\n") + 1
    return (
        f'<details{" open" if open_ else ""} style="margin-top:8px"><summary style="cursor:pointer;font-weight:500;{MUTED}">'
        f'{label} <span style="opacity:.7">· {lines} line{"s" if lines != 1 else ""}</span></summary>'
        f'<pre style="{PRE}">{_colored(text) if not isinstance(body, str) else html.escape(text)}</pre></details>'
    )


def show(response, title=None, check=True, open_response=None):
    """Render one API call. Raises on an HTTP error unless check=False.

    The bodies start open when they are short; open_response forces the response either way.
    """
    request = response.request
    sent = _parse(request.body)
    body = _parse(response.content)
    path = urlsplit(request.url).path
    who = _who(request.url)
    state = state_of(body)
    ms = int(response.elapsed.total_seconds() * 1000)
    status_tone = "good" if response.ok else "bad"
    dsp_error = isinstance(body, dict) and isinstance(body.get("error"), dict)

    head = (
        f'{_method(request.method)} <code style="font-family:{MONO};font-size:12.5px;background:transparent;color:{FG};padding:0">'
        f'{html.escape(path)}</code> <span style="{MUTED}">on</span> <span style="font-weight:600">{html.escape(who)}</span>'
    )
    meta = [f'<span style="{MUTED};font-family:{MONO};font-size:11.5px">{ms} ms</span>', _badge(f"{response.status_code} {response.reason}", status_tone)]
    if state:
        meta.append(_badge(str(state).rsplit(":", 1)[-1], _tone(state)))
    if dsp_error:
        meta.append(_badge("DSP error", "bad"))
    rows = "".join(
        f'<tr style="{ROW}"><td style="{CELL}padding:2px 16px 2px 0;{MUTED};white-space:nowrap;vertical-align:top">{html.escape(k)}</td>'
        f'<td style="{CELL}padding:1px 0;font-family:{MONO};font-size:12px;'
        f'word-break:break-all">{html.escape(str(short(v, 120)))}</td></tr>'
        for k, v in highlights(body)
    )
    parts = []
    if title:
        parts.append(f'<div style="{TITLE}">{html.escape(title)}</div>')
    parts.append(
        '<div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:6px 16px">'
        f'<div style="min-width:0">{head}</div>'
        f'<div style="display:flex;align-items:center;gap:6px;white-space:nowrap">{"".join(meta)}</div></div>'
    )
    if rows:
        parts.append(
            f'<div style="margin:10px 0 2px;padding:6px 10px;border-radius:8px;background:{SOFT};border:1px solid {BORDER}">'
            f'<table style="border-collapse:collapse;margin:0;background:transparent">{rows}</table></div>'
        )
    if sent is not None:
        parts.append(_details("Request body", sent, _short_body(sent)))
    if body is not None:
        parts.append(_details("Response", body, _short_body(body) if open_response is None else open_response))

    text = [f"{request.method} {path} on {who} -> {response.status_code} {response.reason} ({ms} ms)"
            + (f" · {str(state).rsplit(':', 1)[-1]}" if state else "")]
    text += [f"  {k:<14} {short(v, 120)}" for k, v in highlights(body)]
    if body is not None:
        text.append(_json(body) if not isinstance(body, str) else body[:2000])
    display({"text/html": _card("".join(parts)), "text/plain": "\n".join(text)}, raw=True)

    if check:
        response.raise_for_status()
        if dsp_error:
            raise RuntimeError(f"{path}: the agent answered with a DSP error (see above)")
    return body


def _is_number(value):
    return bool(re.fullmatch(r"[+-]?[\d.,]+\s?%?", value))


def _looks_like_code(value):
    """Ids, URLs and DIDs read better in the monospaced font."""
    return value.startswith(("urn:", "did:", "http://", "https://"))


def table(rows, columns, title=None, handle=None):
    """A list of dicts as a table. columns: [(heading, key or function)]."""
    def cell(row, key):
        value = key(row) if callable(key) else row.get(key, "")
        if isinstance(value, float):
            value = f"{value:.2f}"
        return "" if value is None else str(short(value, 60))

    data = [[cell(r, key) for _, key in columns] for r in rows]
    numeric = [bool(data) and all(_is_number(r[i]) for r in data if r[i]) for i in range(len(columns))]
    align = ["text-align:right;font-variant-numeric:tabular-nums;" if n else "" for n in numeric]
    th = "".join(
        f'<th style="{CELL}{a}padding:6px 18px 6px 0;{MUTED};font-weight:500;font-size:11px;text-transform:uppercase;'
        f'letter-spacing:.06em;border-bottom:1px solid {BORDER}">{html.escape(h)}</th>'
        for (h, _), a in zip(columns, align)
    )
    tr = "".join(
        f'<tr class="eu-row" style="{ROW}">'
        + "".join(
            f'<td style="{CELL}{a}padding:6px 18px 6px 0;border-bottom:1px solid {BORDER};'
            f'{f"font-family:{MONO};font-size:12px" if _looks_like_code(value) else ""}">{html.escape(value)}</td>'
            for value, a in zip(r, align)
        )
        + "</tr>"
        for r in data
    )
    caption = f'<div style="{TITLE}">{html.escape(title)}</div>' if title else ""
    page = _card(f'{caption}<table style="border-collapse:collapse;font-size:12.5px;margin:0"><tr>{th}</tr>{tr}</table>')

    widths = [max([len(h)] + [len(r[i]) for r in data]) for i, (h, _) in enumerate(columns)]
    lines = ([title] if title else []) + ["  ".join(h.ljust(w) for (h, _), w in zip(columns, widths))]
    lines += ["  ".join(v.ljust(w) for v, w in zip(r, widths)) for r in data]
    bundle = {"text/html": page, "text/plain": "\n".join(lines)}
    if handle is not None:
        handle.update(bundle, raw=True)
        return handle
    return display(bundle, raw=True, display_id=True)
