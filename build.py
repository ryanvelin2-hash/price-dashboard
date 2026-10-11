#!/usr/bin/env python3
"""Bargain Hunter price dashboard builder.

Usage:
  python3 build.py                          # rebuild dashboard.html from prices.json
  python3 build.py add-observation '<json>' # append one observation (or a JSON list) and rebuild
  python3 build.py add-item '<json>'        # append/replace one item (or a JSON list) and rebuild
  python3 build.py merge <export.json>      # merge an 'Export JSON' file from the dashboard and rebuild
"""
import json, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "prices.json")
OUT = os.path.join(HERE, "dashboard.html")

OBS_KEYS = ["date", "itemId", "store", "product", "pack", "price", "unitPrice",
            "offer", "validUntil", "confirmed", "sourceUrl"]


def load():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def save(d):
    tmp = DATA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, DATA)


def norm_obs(o, items):
    if not isinstance(o, dict):
        raise ValueError("observation must be a JSON object")
    for k in ("itemId", "store", "price"):
        if o.get(k) in (None, ""):
            raise ValueError(f"observation missing required field '{k}'")
    if o["itemId"] not in {i["id"] for i in items}:
        raise ValueError(f"unknown itemId '{o['itemId']}' (add it first with add-item)")
    o.setdefault("date", datetime.date.today().isoformat())
    datetime.date.fromisoformat(o["date"])
    o["price"] = round(float(o["price"]), 2)
    o["unitPrice"] = round(float(o["unitPrice"]), 2) if o.get("unitPrice") not in (None, "") else o["price"]
    o["offer"] = bool(o.get("offer", False))
    o["confirmed"] = bool(o.get("confirmed", True))
    for k in ("product", "pack", "validUntil", "sourceUrl"):
        o.setdefault(k, None)
    return {k: o.get(k) for k in OBS_KEYS} | {k: v for k, v in o.items() if k not in OBS_KEYS}


def same_obs(a, b):
    return all(a.get(k) == b.get(k) for k in ("date", "itemId", "store", "product", "pack"))


def add_observations(d, objs):
    for o in objs:
        o = norm_obs(o, d["items"])
        # same date/item/store/product/pack replaces the old row (re-runs are idempotent)
        d["observations"] = [x for x in d["observations"] if not same_obs(x, o)]
        d["observations"].append(o)


def add_items(d, objs):
    for it in objs:
        for k in ("id", "name", "group", "unit"):
            if not it.get(k):
                raise ValueError(f"item missing required field '{k}'")
        it.setdefault("target", None)
        it.setdefault("source", "")
        it.setdefault("notes", "")
        d["items"] = [x for x in d["items"] if x["id"] != it["id"]] + [it]


def as_list(x):
    return x if isinstance(x, list) else [x]


def build(d):
    payload = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__DATA__", payload).replace(
        "__BUILT__", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {OUT} ({len(d['items'])} items, {len(d['observations'])} observations)")


def main(argv):
    d = load()
    if len(argv) > 1:
        cmd = argv[1]
        try:
            if cmd == "add-observation" and len(argv) == 3:
                add_observations(d, as_list(json.loads(argv[2])))
            elif cmd == "add-item" and len(argv) == 3:
                add_items(d, as_list(json.loads(argv[2])))
            elif cmd == "merge" and len(argv) == 3:
                with open(argv[2], encoding="utf-8") as f:
                    ex = json.load(f)
                add_items(d, ex.get("items", []))
                add_observations(d, ex.get("observations", []))
            else:
                print(__doc__)
                return 2
        except (ValueError, json.JSONDecodeError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        save(d)
    build(d)
    return 0


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bargain Hunter · Price dashboard</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2330;--mute:#6b7280;--line:#e5e7eb;--good:#0a7d3b;--goodbg:#e6f6ec;--warn:#b45309;--accent:#2563eb}
*{box-sizing:border-box}
body{margin:0;font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
header{padding:18px 16px 8px;max-width:1000px;margin:auto}
header h1{margin:0;font-size:22px}
header .meta{color:var(--mute);font-size:13px}
main{max-width:1000px;margin:auto;padding:0 12px 40px}
section.group{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin:14px 0}
section.group h2{margin:0 0 6px;font-size:19px}
h3{font-size:15px;margin:16px 0 6px}
.table-wrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mute);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.03em}
td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
tr.best td{background:var(--goodbg)}
tr.hit td{background:#fff4d6}
.badge{display:inline-block;font-size:11px;padding:1px 6px;border-radius:9px;margin-left:4px;vertical-align:1px}
.b-best{background:var(--good);color:#fff}
.b-offer{background:#dbeafe;color:#1e40af}
.b-hit{background:#f59e0b;color:#fff}
.b-unconf{background:#fee2e2;color:#991b1b}
.small{font-size:12px;color:var(--mute)}
a{color:var(--accent)}
.chart{width:100%;height:auto;display:block;margin:4px 0 2px}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;color:var(--mute)}
.legend i{display:inline-block;width:12px;height:3px;margin-right:5px;vertical-align:middle}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.card{border:1px solid var(--line);border-radius:10px;padding:10px}
form .row{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px}
label{display:block;font-size:12px;color:var(--mute)}
input,select,textarea{width:100%;padding:7px 8px;border:1px solid #cbd5e1;border-radius:7px;font:inherit;background:#fff}
button{padding:8px 14px;border:0;border-radius:8px;background:var(--accent);color:#fff;font:inherit;cursor:pointer;margin:8px 8px 0 0}
button.ghost{background:#e5e7eb;color:var(--ink)}
.note{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:8px 10px;font-size:13px;margin:8px 0}
.local{border-left:3px solid #f59e0b}
</style>
</head>
<body>
<header>
  <h1>Bargain Hunter · Price dashboard</h1>
  <div class="meta">Last updated: <b id="lastUpdated">–</b> · page built __BUILT__ · <span class="small">✱ = unconfirmed price</span></div>
</header>
<main>
  <div id="groups"></div>

  <section class="group" id="addSection">
    <h2>Add item</h2>
    <div class="note">Items added here are saved only in this browser. New items also need a watch set up: ask Bargain Hunter to start tracking them, and send it the exported JSON so it can be merged into prices.json.</div>
    <form id="addForm">
      <div class="row">
        <div><label>Name *</label><input name="name" required placeholder="e.g. Arla letmælk 1 L"></div>
        <div><label>Group *</label><input name="group" required list="groupList" placeholder="Ground beef, Starbucks, …"><datalist id="groupList"></datalist></div>
        <div><label>Unit</label><select name="unit"><option>kr each</option><option>kr/kg</option><option>kr/L</option></select></div>
        <div><label>Target price (optional)</label><input name="target" type="number" step="0.01" min="0"></div>
      </div>
      <div class="row" style="margin-top:8px">
        <div><label>Price source URL</label><input name="source" placeholder="https://…"></div>
        <div><label>Notes</label><input name="notes"></div>
      </div>
      <h3>Optional first price</h3>
      <div class="row">
        <div><label>Store</label><input name="store"></div>
        <div><label>Price (kr)</label><input name="price" type="number" step="0.01" min="0"></div>
        <div><label>Unit price (per unit above)</label><input name="unitPrice" type="number" step="0.01" min="0"></div>
        <div><label>Date</label><input name="date" type="date"></div>
      </div>
      <button type="submit">Add item</button>
      <button type="button" class="ghost" id="exportBtn">Export JSON</button>
      <button type="button" class="ghost" id="clearBtn">Remove browser-added items</button>
    </form>
    <div id="localList" class="small"></div>
  </section>
</main>

<script type="application/json" id="price-data">__DATA__</script>
<script>
(function(){
  "use strict";
  var LS_KEY = "bargainHunter.addedItems.v1";
  var BASE = JSON.parse(document.getElementById("price-data").textContent);
  var COLORS = ["#2563eb","#dc2626","#059669","#d97706","#7c3aed","#db2777","#0891b2","#4b5563"];
  var NEAR = 0.5; // "about 10 kr": at or under target + 0.5 kr counts as a hit

  function loadLocal(){
    try { var x = JSON.parse(localStorage.getItem(LS_KEY) || "null"); if (x && x.items) return x; } catch(e) {}
    return {items: [], observations: []};
  }
  function saveLocal(x){ try { localStorage.setItem(LS_KEY, JSON.stringify(x)); } catch(e) { alert("Could not save to this browser: " + e); } }

  function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function kr(n){ return (n == null || isNaN(n)) ? "–" : Number(n).toFixed(2).replace(".", ",") + " kr"; }
  function safeUrl(u){ return /^https?:\/\//i.test(u || "") ? u : null; }
  function link(u, text){ var s = safeUrl(u); return s ? '<a href="' + esc(s) + '" target="_blank" rel="noopener">' + esc(text) + '</a>' : esc(u || ""); }
  function el(tag, cls, html){ var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function uniq(a){ return a.filter(function(v, i){ return a.indexOf(v) === i; }); }

  function merged(){
    var L = loadLocal();
    var items = BASE.items.slice(), ids = {};
    items.forEach(function(i){ ids[i.id] = 1; });
    L.items.forEach(function(i){ if (!ids[i.id]) { items.push(Object.assign({_local: true}, i)); ids[i.id] = 1; } });
    return {items: items, observations: BASE.observations.concat(L.observations.map(function(o){ return Object.assign({_local: true}, o); }))};
  }

  // Latest observations for one store: all rows from that store's most recent date.
  function latestByStore(obs){
    var by = {};
    obs.forEach(function(o){ (by[o.store] = by[o.store] || []).push(o); });
    var out = {};
    Object.keys(by).forEach(function(s){
      var last = by[s].map(function(o){ return o.date; }).sort().pop();
      out[s] = by[s].filter(function(o){ return o.date === last; }).sort(function(a, b){ return a.unitPrice - b.unitPrice; });
    });
    return out;
  }
  // Series: per store, lowest unitPrice per date.
  function seriesByStore(obs){
    var m = {};
    obs.forEach(function(o){
      var s = m[o.store] = m[o.store] || {};
      var cur = s[o.date];
      if (!cur || o.unitPrice < cur.unitPrice) s[o.date] = o;
    });
    var out = {};
    Object.keys(m).sort().forEach(function(st){
      out[st] = Object.keys(m[st]).sort().map(function(d){ return m[st][d]; });
    });
    return out;
  }

  function dayNum(d){ return Date.parse(d + "T00:00:00Z") / 864e5; }

  function chart(series, target, unit){
    var stores = Object.keys(series);
    var all = [];
    stores.forEach(function(s){ all = all.concat(series[s]); });
    if (!all.length) return el("div", "small", "No price history yet.");
    var W = 640, H = 240, P = {l: 52, r: 12, t: 12, b: 30};
    var dates = uniq(all.map(function(o){ return o.date; })).sort();
    var x0 = dayNum(dates[0]), x1 = dayNum(dates[dates.length - 1]);
    if (x1 === x0) { x0 -= 3; x1 += 3; }
    var vals = all.map(function(o){ return o.unitPrice; });
    if (target != null) vals.push(target);
    var y0 = Math.min.apply(null, vals), y1 = Math.max.apply(null, vals);
    var pad = Math.max((y1 - y0) * 0.12, 1); y0 = Math.max(0, y0 - pad); y1 += pad;
    function X(d){ return P.l + (dayNum(d) - x0) / (x1 - x0) * (W - P.l - P.r); }
    function Y(v){ return P.t + (1 - (v - y0) / (y1 - y0)) * (H - P.t - P.b); }
    var s = '<svg class="chart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="price history">';
    for (var i = 0; i <= 4; i++) {
      var v = y0 + (y1 - y0) * i / 4, y = Y(v);
      s += '<line x1="' + P.l + '" x2="' + (W - P.r) + '" y1="' + y + '" y2="' + y + '" stroke="#eef0f3"/>';
      s += '<text x="' + (P.l - 6) + '" y="' + (y + 4) + '" font-size="11" text-anchor="end" fill="#6b7280">' + v.toFixed(0) + '</text>';
    }
    var step = Math.max(1, Math.ceil(dates.length / 6));
    dates.forEach(function(d, i){
      if (i % step && i !== dates.length - 1) return;
      s += '<text x="' + X(d) + '" y="' + (H - 10) + '" font-size="11" text-anchor="middle" fill="#6b7280">' + d.slice(5) + '</text>';
    });
    s += '<text x="6" y="' + (P.t + 4) + '" font-size="10" fill="#6b7280">' + esc(unit) + '</text>';
    if (target != null) {
      var ty = Y(target);
      s += '<line x1="' + P.l + '" x2="' + (W - P.r) + '" y1="' + ty + '" y2="' + ty + '" stroke="#f59e0b" stroke-width="2" stroke-dasharray="6 5"/>';
      s += '<text x="' + (W - P.r) + '" y="' + (ty - 5) + '" font-size="11" text-anchor="end" fill="#b45309">target ' + target + ' kr</text>';
    }
    stores.forEach(function(st, k){
      var c = COLORS[k % COLORS.length], pts = series[st];
      if (pts.length > 1) s += '<polyline fill="none" stroke="' + c + '" stroke-width="2.2" points="' + pts.map(function(o){ return X(o.date) + "," + Y(o.unitPrice); }).join(" ") + '"/>';
      pts.forEach(function(o){
        var t = esc(st + " · " + o.date + " · " + kr(o.unitPrice) + (o.confirmed === false ? " (unconfirmed)" : "") + (o.offer ? " (offer)" : ""));
        if (o.confirmed === false) {
          s += '<circle cx="' + X(o.date) + '" cy="' + Y(o.unitPrice) + '" r="5" fill="#fff" stroke="' + c + '" stroke-width="2" stroke-dasharray="2 2"><title>' + t + '</title></circle>';
        } else {
          s += '<circle cx="' + X(o.date) + '" cy="' + Y(o.unitPrice) + '" r="4" fill="' + c + '"><title>' + t + '</title></circle>';
        }
      });
    });
    s += '</svg>';
    var wrap = el("div", null, s);
    wrap.appendChild(el("div", "legend", stores.map(function(st, k){
      return '<span><i style="background:' + COLORS[k % COLORS.length] + '"></i>' + esc(st) + '</span>';
    }).join("") + (target != null ? '<span><i style="background:repeating-linear-gradient(90deg,#f59e0b 0 5px,transparent 5px 9px)"></i>target</span>' : "") + '<span>hollow dot = unconfirmed</span>'));
    return wrap;
  }

  function obsCell(o){
    return esc(o.product || "") + (o.pack ? ' <span class="small">' + esc(o.pack) + '</span>' : "") +
      (o.offer ? '<span class="badge b-offer">offer' + (o.validUntil ? " to " + esc(o.validUntil) : "") + '</span>' : "") +
      (o.confirmed === false ? '<span class="badge b-unconf">✱ unconfirmed</span>' : "") +
      (o._local ? '<span class="badge b-unconf" style="background:#fef3c7;color:#92400e">browser only</span>' : "");
  }

  // Ground-beef-style group: one comparison across stores by unit price, cheapest highlighted.
  function renderComparison(sec, items, obs){
    items.forEach(function(it){
      var io = obs.filter(function(o){ return o.itemId === it.id; });
      sec.appendChild(el("h3", null, esc(it.name) + ' <span class="small">(' + esc(it.unit) + ')</span>'));
      if (it.notes) sec.appendChild(el("div", "small", esc(it.notes)));
      var latest = latestByStore(io), stores = Object.keys(latest);
      var best = null;
      stores.forEach(function(s){ var o = latest[s][0]; if (!best || o.unitPrice < best.unitPrice) best = o; });
      stores.sort(function(a, b){ return latest[a][0].unitPrice - latest[b][0].unitPrice; });
      var rows = stores.map(function(s){
        var top = latest[s][0], isBest = best && top.unitPrice === best.unitPrice;
        var others = latest[s].slice(1).map(function(o){ return '<div class="small">' + obsCell(o) + " · " + kr(o.price) + " · " + kr(o.unitPrice).replace(" kr", " kr/kg") + " " + link(o.sourceUrl, "src") + '</div>'; }).join("");
        return '<tr class="' + (isBest ? "best" : "") + '"><td><b>' + esc(s) + '</b>' + (isBest ? '<span class="badge b-best">cheapest</span>' : "") +
          '<div class="small">' + esc(top.date) + '</div></td><td>' + obsCell(top) + " " + link(top.sourceUrl, "src") + others +
          '</td><td class="num">' + kr(top.price) + '</td><td class="num"><b>' + kr(top.unitPrice) + '</b></td></tr>';
      }).join("");
      var t = el("div", "table-wrap", '<table><thead><tr><th>Store</th><th>Cheapest product (latest)</th><th class="num">Pack price</th><th class="num">' + esc(it.unit) + '</th></tr></thead><tbody>' + (rows || '<tr><td colspan="4" class="small">No prices yet.</td></tr>') + '</tbody></table>');
      sec.appendChild(t);
      sec.appendChild(el("div", "small", "History: lowest " + esc(it.unit) + " per store per day."));
      sec.appendChild(chart(seriesByStore(io), it.target, it.unit));
    });
  }

  // Product-card group (Starbucks and added items): latest price per store per product + chart.
  function renderCards(sec, items, obs){
    var grid = el("div", "grid");
    items.forEach(function(it){
      var io = obs.filter(function(o){ return o.itemId === it.id; });
      var card = el("div", "card" + (it._local ? " local" : ""));
      card.appendChild(el("h3", null, esc(it.name)));
      var meta = [esc(it.unit)];
      if (it.target != null) meta.push("target " + kr(it.target));
      if (it.source) meta.push(link(it.source, "source"));
      if (it._local) meta.push("added in this browser");
      card.appendChild(el("div", "small", meta.join(" · ")));
      var latest = latestByStore(io), rows = [];
      Object.keys(latest).forEach(function(s){ latest[s].forEach(function(o){ rows.push(o); }); });
      rows.sort(function(a, b){ return a.unitPrice - b.unitPrice; });
      var html = rows.map(function(o){
        var hit = it.target != null && o.unitPrice <= it.target + NEAR;
        return '<tr class="' + (hit ? "hit" : "") + '"><td><b>' + esc(o.store) + '</b>' + (hit ? '<span class="badge b-hit">≈ target</span>' : "") + '<div class="small">' + esc(o.date) + " · " + link(o.sourceUrl, "src") + '</div></td><td>' + obsCell(o) + '</td><td class="num"><b>' + kr(o.unitPrice) + '</b>' + (o.confirmed === false ? " ✱" : "") + '</td></tr>';
      }).join("");
      card.appendChild(el("div", "table-wrap", '<table><thead><tr><th>Store</th><th>Product</th><th class="num">Price</th></tr></thead><tbody>' + (html || '<tr><td colspan="3" class="small">No prices yet — ask Bargain Hunter to set up a watch.</td></tr>') + '</tbody></table>'));
      card.appendChild(chart(seriesByStore(io), it.target, it.unit));
      grid.appendChild(card);
    });
    sec.appendChild(grid);
  }

  function render(){
    var D = merged(), root = document.getElementById("groups");
    root.innerHTML = "";
    var groups = uniq(D.items.map(function(i){ return i.group; }));
    var dates = D.observations.map(function(o){ return o.date; }).sort();
    document.getElementById("lastUpdated").textContent = dates.length ? dates[dates.length - 1] : "no data yet";
    document.getElementById("groupList").innerHTML = groups.map(function(g){ return '<option value="' + esc(g) + '">'; }).join("");
    groups.forEach(function(g){
      var items = D.items.filter(function(i){ return i.group === g; });
      var sec = el("section", "group");
      sec.appendChild(el("h2", null, esc(g)));
      var cmp = items.length === 1 && items[0].unit === "kr/kg";
      (cmp ? renderComparison : renderCards)(sec, items, D.observations);
      root.appendChild(sec);
    });
    var L = loadLocal();
    document.getElementById("localList").innerHTML = L.items.length ? "Added in this browser: " + L.items.map(function(i){ return esc(i.name); }).join(", ") : "";
  }

  function slug(s){ return "user-" + s.toLowerCase().normalize("NFKD").replace(/[^\w]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) + "-" + Date.now().toString(36); }
  function num(v){ return v === "" || v == null ? null : Number(v); }

  document.getElementById("addForm").addEventListener("submit", function(ev){
    ev.preventDefault();
    var f = ev.target, g = function(n){ return f.elements[n].value.trim(); };
    if (!g("name") || !g("group")) return;
    var item = {id: slug(g("name")), name: g("name"), group: g("group"), unit: g("unit"), target: num(g("target")), source: g("source"), notes: g("notes")};
    var L = loadLocal();
    L.items.push(item);
    var p = num(g("price"));
    if (p != null && !isNaN(p)) {
      L.observations.push({date: g("date") || new Date().toISOString().slice(0, 10), itemId: item.id, store: g("store") || "unknown store",
        product: item.name, pack: null, price: p, unitPrice: num(g("unitPrice")) != null ? num(g("unitPrice")) : p,
        offer: false, validUntil: null, confirmed: false, sourceUrl: item.source || null});
    }
    saveLocal(L); f.reset(); render();
  });
  document.getElementById("exportBtn").addEventListener("click", function(){
    var L = loadLocal();
    var blob = new Blob([JSON.stringify(L, null, 2)], {type: "application/json"});
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "bargain-hunter-added-items.json";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function(){ URL.revokeObjectURL(a.href); }, 1000);
  });
  document.getElementById("clearBtn").addEventListener("click", function(){
    if (confirm("Remove all items added in this browser?")) { localStorage.removeItem(LS_KEY); render(); }
  });
  render();
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main(sys.argv))
