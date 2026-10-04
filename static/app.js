(function () {
  var root = document.documentElement;
  var tb = document.getElementById('theme-toggle');
  function icon() { if (tb) tb.textContent = root.dataset.theme === 'dark' ? '☀ Light mode' : '☾ Dark mode'; }
  icon();
  if (tb) tb.addEventListener('click', function () {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('af-theme', root.dataset.theme); } catch (e) {}
    icon();
  });

  var mb = document.getElementById('menu-btn');
  if (mb) mb.addEventListener('click', function () { document.body.classList.toggle('nav-open'); });

  document.querySelectorAll('form[data-confirm]').forEach(function (f) {
    f.addEventListener('submit', function (ev) { if (!confirm(f.dataset.confirm)) ev.preventDefault(); });
  });

  document.querySelectorAll('[data-toggle-all]').forEach(function (b) {
    b.addEventListener('click', function () {
      var all = document.querySelectorAll('details.run');
      var open = Array.prototype.some.call(all, function (d) { return !d.open; });
      all.forEach(function (d) { d.open = open; });
    });
  });

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmt(v) { return v >= 100 ? Math.round(v) : +Number(v).toPrecision(2); }

  function drawBars(el) {
    var d = JSON.parse(el.dataset.chart);
    var W = Math.max(el.clientWidth, 260), H = +el.dataset.h || 220;
    var p = { l: 50, r: 12, t: 16, b: 34 };
    var max = Math.max.apply(null, d.values.concat([0]));
    var top = el.dataset.int ? (Math.ceil(max / 4) * 4 || 4) : (max * 1.15 || 1);
    var iw = W - p.l - p.r, ih = H - p.t - p.b, n = d.values.length || 1, bw = Math.min(64, iw / n * 0.6);
    var s = '<svg width="' + W + '" height="' + H + '" role="img">';
    for (var i = 0; i <= 4; i++) {
      var y = p.t + ih - ih * i / 4;
      s += '<line class="grid" x1="' + p.l + '" x2="' + (W - p.r) + '" y1="' + y + '" y2="' + y + '"/>' +
           '<text class="axis" x="' + (p.l - 6) + '" y="' + (y + 4) + '" text-anchor="end">' + fmt(top * i / 4) + '</text>';
    }
    d.values.forEach(function (v, i) {
      var cx = p.l + iw / n * (i + 0.5), h = ih * v / top;
      s += '<rect class="bar bar' + (i % 2) + '" x="' + (cx - bw / 2) + '" y="' + (p.t + ih - h) + '" width="' + bw + '" height="' + h + '" rx="5"/>' +
           '<text class="val" x="' + cx + '" y="' + (p.t + ih - h - 5) + '" text-anchor="middle">' + fmt(v) + '</text>' +
           '<text class="axis" x="' + cx + '" y="' + (H - 12) + '" text-anchor="middle">' + esc(d.labels[i]) + '</text>';
    });
    el.innerHTML = s + '</svg>';
  }
  function drawAll() { document.querySelectorAll('[data-chart]').forEach(drawBars); }
  drawAll();
  window.addEventListener('resize', drawAll);
})();
