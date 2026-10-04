(function () {
  var data = JSON.parse(document.getElementById('editor-data').textContent);
  var agents = {};
  data.agents.forEach(function (a) { agents[a.id] = a; });
  var nodes = data.workflow.nodes.map(function (n) { return Object.assign({}, n); });
  var edges = data.workflow.edges.map(function (e) { return Object.assign({}, e); });
  var sel = null, drag = null, conn = null, dirty = false;
  var svg = document.getElementById('canvas'), NS = 'http://www.w3.org/2000/svg', W = 190, H = 64;
  var statusEl = document.getElementById('status'), delBtn = document.getElementById('del-btn');
  var counter = nodes.reduce(function (m, n) { return Math.max(m, parseInt(String(n.id).replace(/\D/g, '')) || 0); }, 0);

  function hue(s) { return Array.from(s || '').reduce(function (a, c) { return a + c.charCodeAt(0); }, 0) % 360; }
  function mk(tag, attrs, parent, text) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text !== undefined) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function pos(ev) { var r = svg.getBoundingClientRect(); return { x: ev.clientX - r.left, y: ev.clientY - r.top }; }
  function byId(id) { return nodes.find(function (n) { return n.id === id; }); }
  function setStatus(t, err) { statusEl.textContent = t; statusEl.style.color = err ? 'var(--danger)' : ''; }
  function touch() { dirty = true; setStatus('Unsaved changes'); }
  function select(s) { sel = s; delBtn.disabled = !sel; render(); }
  function cut(s, n) { return s.length > n ? s.slice(0, n - 1) + '…' : s; }
  function reaches(a, b, seen) {
    seen = seen || {};
    if (a === b) return true;
    if (seen[a]) return false;
    seen[a] = true;
    return edges.some(function (e) { return e.from === a && reaches(e.to, b, seen); });
  }

  function addEdge(f, t) {
    if (f === t) { render(); return setStatus('A node cannot connect to itself.', true); }
    if (edges.some(function (e) { return e.from === f && e.to === t; })) { render(); return setStatus('That connection already exists.', true); }
    if (reaches(t, f)) { render(); return setStatus('That connection would create a loop.', true); }
    edges.push({ from: f, to: t });
    touch();
    select({ type: 'edge', key: f + '>' + t });
  }
  function addNode(agentId, x, y) {
    counter++;
    var n = { id: 'n' + counter, agent_id: agentId, x: Math.max(0, Math.round(x)), y: Math.max(0, Math.round(y)) };
    nodes.push(n);
    touch();
    select({ type: 'node', id: n.id });
  }
  function removeSel() {
    if (!sel) return;
    if (sel.type === 'node') {
      nodes = nodes.filter(function (n) { return n.id !== sel.id; });
      edges = edges.filter(function (e) { return e.from !== sel.id && e.to !== sel.id; });
    } else {
      edges = edges.filter(function (e) { return e.from + '>' + e.to !== sel.key; });
    }
    touch();
    select(null);
  }

  function render() {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    var defs = mk('defs', {}, svg);
    var mr = mk('marker', { id: 'arrow', viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse' }, defs);
    mk('path', { d: 'M0,0 L10,5 L0,10 z', class: 'arrowhead' }, mr);
    var eg = mk('g', {}, svg), ng = mk('g', {}, svg);

    edges.forEach(function (e) {
      var a = byId(e.from), b = byId(e.to);
      if (!a || !b) return;
      var x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2, dx = Math.max(50, Math.abs(x2 - x1) / 2);
      var d = 'M' + x1 + ',' + y1 + ' C' + (x1 + dx) + ',' + y1 + ' ' + (x2 - dx) + ',' + y2 + ' ' + x2 + ',' + y2;
      var key = e.from + '>' + e.to, on = sel && sel.type === 'edge' && sel.key === key;
      mk('path', { d: d, class: 'edge' + (on ? ' sel' : ''), 'marker-end': 'url(#arrow)' }, eg);
      var hit = mk('path', { d: d, class: 'edge-hit' }, eg);
      hit.addEventListener('pointerdown', function (ev) { ev.stopPropagation(); select({ type: 'edge', key: key }); });
    });

    nodes.forEach(function (n) {
      var a = agents[n.agent_id], on = sel && sel.type === 'node' && sel.id === n.id;
      var g = mk('g', { transform: 'translate(' + n.x + ',' + n.y + ')', class: 'node' + (on ? ' sel' : '') }, ng);
      var rect = mk('rect', { class: 'node-rect', width: W, height: H, rx: 14 }, g);
      var role = a ? a.role : 'Missing';
      var bw = Math.min(W - 24, role.length * 6.4 + 16);
      mk('rect', { x: 12, y: 10, width: bw, height: 18, rx: 9, fill: a ? 'hsl(' + hue(role) + ' 65% 48%)' : '#dc2626' }, g);
      mk('text', { x: 12 + bw / 2, y: 22.5, class: 'node-badge', 'text-anchor': 'middle' }, g, cut(role, 24));
      mk('text', { x: 14, y: 50, class: 'node-name' }, g, a ? cut(a.name, 24) : 'Agent deleted');
      mk('circle', { cx: 0, cy: H / 2, r: 6, class: 'port' }, g);
      var pout = mk('circle', { cx: W, cy: H / 2, r: 7, class: 'port out' }, g);
      rect.addEventListener('pointerdown', function (ev) {
        ev.stopPropagation();
        var p = pos(ev);
        drag = { id: n.id, dx: p.x - n.x, dy: p.y - n.y };
        select({ type: 'node', id: n.id });
      });
      pout.addEventListener('pointerdown', function (ev) {
        ev.stopPropagation(); ev.preventDefault();
        var p = pos(ev);
        conn = { from: n.id, x: p.x, y: p.y };
        render();
      });
    });

    if (conn) {
      var a2 = byId(conn.from);
      if (a2) mk('path', { d: 'M' + (a2.x + W) + ',' + (a2.y + H / 2) + ' L' + conn.x + ',' + conn.y, class: 'edge temp' }, svg);
    }
    if (!nodes.length) mk('text', { x: 400, y: 200, class: 'hint' }, svg, 'Drag an agent from the left panel onto this canvas');
  }

  window.addEventListener('pointermove', function (ev) {
    if (drag) {
      var p = pos(ev), n = byId(drag.id);
      if (n) { n.x = Math.max(0, Math.round(p.x - drag.dx)); n.y = Math.max(0, Math.round(p.y - drag.dy)); touch(); render(); }
    } else if (conn) {
      var q = pos(ev); conn.x = q.x; conn.y = q.y; render();
    }
  });
  window.addEventListener('pointerup', function (ev) {
    if (conn) {
      var p = pos(ev), f = conn.from;
      var t = nodes.find(function (n) { return p.x >= n.x && p.x <= n.x + W && p.y >= n.y && p.y <= n.y + H; });
      conn = null;
      if (t) addEdge(f, t.id); else render();
    }
    drag = null;
  });
  window.addEventListener('pointercancel', function () { drag = null; conn = null; render(); });
  svg.addEventListener('pointerdown', function () { select(null); });

  window.addEventListener('keydown', function (ev) {
    var tag = (ev.target.tagName || '').toLowerCase();
    if ((ev.key === 'Delete' || ev.key === 'Backspace') && tag !== 'input' && tag !== 'textarea') { ev.preventDefault(); removeSel(); }
  });
  delBtn.addEventListener('click', removeSel);

  document.querySelectorAll('.pal-item').forEach(function (it) {
    it.addEventListener('dragstart', function (ev) { ev.dataTransfer.setData('text/plain', it.dataset.agent); ev.dataTransfer.effectAllowed = 'copy'; });
    it.addEventListener('click', function () { var k = nodes.length; addNode(it.dataset.agent, 30 + (k % 4) * 40, 30 + (k % 6) * 50); });
  });
  svg.addEventListener('dragover', function (ev) { ev.preventDefault(); });
  svg.addEventListener('drop', function (ev) {
    ev.preventDefault();
    var id = ev.dataTransfer.getData('text/plain');
    if (agents[id]) { var p = pos(ev); addNode(id, p.x - W / 2, p.y - H / 2); }
  });

  var nameInput = document.getElementById('wf-name');
  nameInput.addEventListener('input', touch);

  function save() {
    setStatus('Saving…');
    return fetch(data.save_url, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: nameInput.value, nodes: nodes, edges: edges })
    }).then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || 'Save failed'); return j; }); })
      .then(function (j) { dirty = false; setStatus('Saved · ' + j.nodes + ' agents, ' + j.edges + ' connections'); return true; })
      .catch(function (e) { setStatus(e.message, true); return false; });
  }
  document.getElementById('save-btn').addEventListener('click', save);

  var runForm = document.getElementById('run-form');
  runForm.addEventListener('submit', function (ev) {
    ev.preventDefault();
    if (!nodes.length) { setStatus('Add at least one agent before running.', true); return; }
    save().then(function (ok) { if (ok) { dirty = false; runForm.submit(); } });
  });

  window.addEventListener('beforeunload', function (ev) { if (dirty) { ev.preventDefault(); ev.returnValue = ''; } });
  render();
})();
