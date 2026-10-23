// Crossover on the TV. The laptop sends a ready-made view (projection, copy and
// chart already worked out); this page lays it out for the big screen. Amounts
// start hidden; OK shows or hides them.
(function () {
  'use strict';

  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  // Widths of the month names in em, measured in the hero's own type once the
  // font has loaded, so the month window fits each name exactly.
  var MONTH_EM = null;
  var DAY = 86400000;
  var STALE_DAYS = 14;
  var MASK = '$••••';

  var hidden = true;
  var view = null;
  var seen = { previous: null, fresh: false };

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function svg(tag, attrs, text) {
    var node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.keys(attrs || {}).forEach(function (k) {
      node.setAttribute(k, attrs[k]);
    });
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function day(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
    return m ? new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])) : null;
  }

  function today() {
    var now = new Date();
    return new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
  }

  function fmtDate(d) {
    return d.getUTCDate() + ' ' + MONTHS[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
  }

  function count(n) {
    return Math.round(n).toLocaleString('en-NZ');
  }

  function span(days) {
    var d = Math.abs(days);
    if (d < 0.95) return 'less than a day';
    if (d < 10) return (Math.round(d * 10) / 10) + (Math.round(d * 10) === 10 ? ' day' : ' days');
    if (d < 400) return Math.round(d) + ' days';
    var months = Math.round(d / (365.2425 / 12));
    var y = Math.floor(months / 12);
    var mo = months % 12;
    var ys = y + (y === 1 ? ' year' : ' years');
    return mo === 0 ? ys : ys + ' ' + mo + (mo === 1 ? ' month' : ' months');
  }

  function compactMoney(x) {
    var a = Math.abs(x);
    var sign = x < 0 ? '−' : '';
    if (a >= 1e6) return sign + '$' + (a / 1e6).toFixed(a % 1e6 === 0 ? 0 : 1) + 'M';
    if (a >= 1e3) return sign + '$' + Math.round(a / 1e3) + 'k';
    return sign + '$' + Math.round(a);
  }

  /** Text with money in separate segments, so amounts can be hidden. */
  function segs(parent, list) {
    (list || []).forEach(function (s) {
      if (s.t !== undefined) parent.appendChild(document.createTextNode(s.t));
      else parent.appendChild(el('span', hidden ? 'amt is-hidden' : 'amt', hidden ? MASK : s.m));
    });
    return parent;
  }

  // Since the last look: the comparison stays until the date changes again.
  // The app keeps it in its preferences; a browser keeps it in localStorage.
  function readJson(key) {
    try {
      var app = window.CrossoverTv;
      var raw = app && app.get ? app.get(key) : window.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function writeJson(key, value) {
    try {
      var app = window.CrossoverTv;
      if (app && app.put) app.put(key, JSON.stringify(value));
      else window.localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      /* Storage is optional. */
    }
  }

  function recordView(date) {
    var now = { at: new Date().toISOString(), date: date };
    var last = readJson('crossover.tv.last');
    var previous = readJson('crossover.tv.previous');
    var fresh = false;
    if (last && last.date !== date) {
      previous = last;
      fresh = true;
      writeJson('crossover.tv.previous', previous);
    }
    writeJson('crossover.tv.last', now);
    return { previous: previous, fresh: fresh };
  }

  function measureMonths() {
    // A hidden copy of the hero date, so the probe has its size and spacing.
    var host = el('h1', 'hero-date');
    host.style.cssText = 'position:absolute;visibility:hidden;left:-9999px;top:0';
    var probe = el('span');
    probe.style.whiteSpace = 'nowrap';
    host.appendChild(probe);
    document.body.appendChild(host);
    var size = parseFloat(getComputedStyle(probe).fontSize);
    MONTH_EM = MONTHS.map(function (name) {
      probe.textContent = name;
      return probe.getBoundingClientRect().width / size;
    });
    document.body.removeChild(host);
  }

  function odometer(date, from) {
    var root = el('span', 'odo');
    root.setAttribute('role', 'img');
    root.setAttribute('aria-label', MONTHS[date.getUTCMonth()] + ' ' + date.getUTCFullYear());
    var shown = from || date;
    var to = date.getUTCMonth();
    var start = from ? from.getUTCMonth() : to;
    var passed = MONTH_EM.slice(Math.min(start, to), Math.max(start, to) + 1);
    var month = el('span', 'odo-col odo-month' + (from ? ' is-rolling' : ''));
    month.style.width = Math.max.apply(null, passed) + 'em';
    var mStrip = el('span', 'odo-strip');
    MONTHS.forEach(function (name) {
      mStrip.appendChild(el('span', null, name));
    });
    mStrip.style.transform = 'translateY(calc(var(--h) * ' + -shown.getUTCMonth() + '))';
    month.appendChild(mStrip);
    root.appendChild(month);
    root.appendChild(el('span', 'odo-space'));
    var strips = [];
    var shownYear = String(shown.getUTCFullYear());
    for (var i = 0; i < 4; i++) {
      var col = el('span', 'odo-col');
      col.appendChild(el('span', 'odo-size', '0'));
      var strip = el('span', 'odo-strip');
      for (var d = 0; d < 10; d++) strip.appendChild(el('span', null, String(d)));
      strip.style.transform = 'translateY(calc(var(--h) * ' + -Number(shownYear[i]) + '))';
      strip.style.transitionDelay = (3 - i) * 80 + 'ms';
      col.appendChild(strip);
      root.appendChild(col);
      strips.push(strip);
    }
    if (from) {
      // Two frames later, roll to the new date and close the month window.
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          var year = String(date.getUTCFullYear());
          mStrip.style.transform = 'translateY(calc(var(--h) * ' + -to + '))';
          month.style.width = MONTH_EM[to] + 'em';
          strips.forEach(function (s, i) {
            s.style.transform = 'translateY(calc(var(--h) * ' + -Number(year[i]) + '))';
          });
        });
      });
    }
    return root;
  }

  function hero() {
    var box = el('section', 'hero');
    box.appendChild(el('p', 'hero-label', view.goal.label));
    var date = day(view.goal.date);
    if (!date) {
      box.appendChild(el('h1', 'hero-date', 'Not reached'));
      return box;
    }
    var prev = seen.previous ? day(seen.previous.date) : null;
    var h1 = el('h1', 'hero-date');
    box.appendChild(h1);
    if (!MONTH_EM) measureMonths();
    h1.appendChild(odometer(date, seen.fresh ? prev : null));
    var left = Math.max(0, Math.round((date - today()) / DAY));
    var line = el('p', 'hero-line');
    line.appendChild(el('strong', null, count(left) + ' days'));
    line.appendChild(document.createTextNode(' from today, at age ' + view.goal.age + '.'));
    box.appendChild(line);
    if (seen.previous) {
      var at = day(seen.previous.at);
      var moved = prev ? (date - prev) / DAY : 0;
      var since = el('p', 'hero-since' + (Math.abs(moved) >= 0.5 ? ' is-moved' : ''));
      if (Math.abs(moved) >= 0.5) {
        var words = span(moved) + (moved < 0 ? ' earlier' : ' later');
        since.appendChild(el('strong', null, words.charAt(0).toUpperCase() + words.slice(1)));
        since.appendChild(document.createTextNode(' than when you last looked, on ' + fmtDate(at) + '.'));
      } else {
        since.textContent = 'Unchanged since you last looked, on ' + fmtDate(at) + '.';
      }
      box.appendChild(since);
    }
    if (view.price) box.appendChild(segs(el('p', 'price'), view.price));
    return box;
  }

  function route() {
    var box = el('section', 'route');
    var list = el('ol', 'waypoints');
    var activeIndex = -1;
    view.stages.forEach(function (s, i) {
      if (s.state === 'active') activeIndex = i;
    });
    view.stages.forEach(function (s, i) {
      var li = el('li', 'wp wp-' + s.kind + ' is-' + s.state + (i === activeIndex - 1 ? ' before-active' : ''));
      li.appendChild(el('span', 'node'));
      li.appendChild(el('p', 'wp-name', s.name));
      li.appendChild(el('p', 'wp-date', s.date));
      if (s.short && s.short.length) li.appendChild(segs(el('p', 'wp-short'), s.short));
      if (s.state === 'active' && s.progress !== null && s.progress !== undefined) {
        var bar = el('div', 'wp-progress');
        var fill = el('span');
        fill.style.width = Math.max(0, Math.min(1, s.progress)) * 100 + '%';
        bar.appendChild(fill);
        li.appendChild(bar);
      }
      list.appendChild(li);
    });
    box.appendChild(list);
    if (view.instruction) {
      var note = el('div', 'instruction');
      note.appendChild(segs(el('p'), view.instruction));
      if (view.record) note.appendChild(el('p', 'record', view.record));
      box.appendChild(note);
    }
    return box;
  }

  function chartBox() {
    var box = el('section', 'chart');
    box.appendChild(el('h2', 'chart-title', view.chart.title));
    box.appendChild(el('p', 'chart-note', view.chart.note));
    box.appendChild(el('div', 'chart-plot'));
    return box;
  }

  /** Draws the chart once its box has a size. */
  function drawChart(box) {
    var c = view.chart;
    var rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
    var plot = box.querySelector('.chart-plot');
    var rect = plot.getBoundingClientRect();
    var width = rect.width;
    var height = Math.max(14 * rem, rect.height);
    var pad = { t: 3.2 * rem, b: 3.6 * rem };
    var end = c.position.length - 1;
    var values = c.position.concat(c.needed);
    var lo = Math.min.apply(null, values.concat([0]));
    var hi = Math.max.apply(null, values);
    var raw = (hi - lo) / 4;
    var mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var norm = raw / mag;
    var step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10) * mag;
    var y0 = Math.floor(lo / step) * step;
    var y1 = Math.ceil(hi / step) * step;
    var ih = height - pad.t - pad.b;
    // Amounts sit in a gutter on the left, clear of the lines.
    var left = 5 * rem;
    function x(m) { return left + (m / end) * (width - left); }
    function y(v) { return pad.t + (1 - (v - y0) / (y1 - y0)) * ih; }
    function line(vals) {
      return vals.map(function (v, i) { return (i ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(v).toFixed(1); }).join('');
    }
    var fs = 1.3 * rem;
    var s = svg('svg', { width: width, height: height, viewBox: '0 0 ' + width + ' ' + height, role: 'img' });
    s.appendChild(svg('title', {}, c.title));
    for (var v = y0; v <= y1 + step / 2; v += step) {
      var gy = y(v);
      s.appendChild(svg('line', { x1: left, x2: width, y1: gy, y2: gy, class: v === 0 ? 'grid zero' : 'grid' }));
      s.appendChild(svg('text', { x: left - 0.9 * rem, y: gy + 0.45 * rem, 'text-anchor': 'end', class: 'tick', 'font-size': fs }, hidden ? '•••' : compactMoney(Math.round(v))));
    }
    if (c.zero_label && y0 < 0) {
      s.appendChild(svg('text', { x: x(0) + 1.2 * rem, y: y(0) - 0.6 * rem, class: 'tick halo', 'font-size': fs, 'stroke-width': 0.4 * rem }, c.zero_label));
    }
    // Years along the bottom, with the age under each.
    var start = day(c.start);
    // A year label needs about 5rem; skip years until they fit.
    var perYear = (width - left) / (end / 12);
    var every = perYear >= 5 * rem ? 1 : perYear >= 2.5 * rem ? 2 : perYear >= 1.25 * rem ? 4 : 5;
    for (var yr = start.getUTCFullYear() + 1, k = 0; ; yr++, k++) {
      var month = (Date.UTC(yr, 0, 1) - start) / DAY / (365.2425 / 12);
      if (month > end) break;
      if (k % every) continue;
      var tx = x(month);
      var anchor = tx > width - 2 * rem ? 'end' : 'middle';
      s.appendChild(svg('line', { x1: tx, x2: tx, y1: height - pad.b, y2: height - pad.b + 0.4 * rem, class: 'grid' }));
      s.appendChild(svg('text', { x: tx, y: height - pad.b + 1.7 * rem, 'text-anchor': anchor, class: 'tick', 'font-size': fs }, String(yr)));
      s.appendChild(svg('text', { x: tx, y: height - pad.b + 3.1 * rem, 'text-anchor': anchor, class: 'tick', 'font-size': 1.15 * rem }, (k === 0 ? 'age ' : '') + Math.floor(c.age + month / 12)));
    }
    s.appendChild(svg('path', { d: line(c.needed), class: 'ln-needed', 'stroke-width': 0.17 * rem }));
    s.appendChild(svg('path', { d: line(c.position), class: 'ln-position', 'stroke-width': 0.28 * rem }));
    var na = Math.round(end * 0.04);
    s.appendChild(svg('text', { x: x(na), y: y(c.needed[na]) - 0.9 * rem, class: 'lbl-needed halo', 'font-size': fs, 'stroke-width': 0.45 * rem }, 'Money needed'));
    var pa = Math.round(end * 0.3);
    s.appendChild(svg('text', { x: x(pa) + rem, y: y(c.position[pa]) + 2.2 * rem, class: 'lbl-position halo', 'font-size': fs, 'stroke-width': 0.45 * rem }, 'Position'));
    s.appendChild(svg('circle', { cx: x(0), cy: y(c.position[0]), r: 0.45 * rem, class: 'now' }));
    if (c.crossing !== null && c.crossing <= end) {
      var i0 = Math.floor(c.crossing);
      var f = c.crossing - i0;
      var a = c.needed[i0];
      var b = c.needed[Math.min(end, i0 + 1)];
      var mx = x(c.crossing);
      var my = y(a + (b - a) * f);
      var r = 0.75 * rem;
      var g = svg('g', { class: 'mark' });
      g.appendChild(svg('line', { x1: mx, x2: mx, y1: 1.3 * rem, y2: height - pad.b, class: 'leader', 'stroke-width': 1.5 }));
      g.appendChild(svg('path', { d: 'M' + mx + ',' + (my - r) + 'L' + (mx + r) + ',' + my + 'L' + mx + ',' + (my + r) + 'L' + (mx - r) + ',' + my + 'Z' }));
      var anchorX = mx > width - 14 * rem ? 'end' : mx < left + 14 * rem ? 'start' : 'middle';
      g.appendChild(svg('text', { x: mx, y: 0.6 * rem, 'text-anchor': anchorX, 'font-size': 1.45 * rem }, c.crossing_label));
      s.appendChild(g);
    }
    plot.appendChild(s);
  }

  function render() {
    var screen = document.getElementById('screen');
    screen.textContent = '';
    if (!view) {
      var empty = el('div', 'empty');
      empty.appendChild(el('h1', null, 'No data on this TV yet'));
      empty.appendChild(el('p', null, 'Publish the data file from the laptop and it appears here within a few seconds.'));
      screen.appendChild(empty);
      return;
    }
    var bar = el('header', 'bar');
    bar.appendChild(el('span', 'brand', 'Crossover'));
    var read = day(view.read.date);
    var age = read ? Math.floor((today() - read) / DAY) : 0;
    bar.appendChild(el('span', 'read' + (age > STALE_DAYS ? ' is-stale' : ''), age > STALE_DAYS ? 'Data is ' + age + ' days old' : view.read.label));
    bar.appendChild(el('span', 'hint', hidden ? 'Press OK to show amounts' : 'Press OK to hide amounts'));
    screen.appendChild(bar);

    var top = el('div', 'top');
    top.appendChild(hero());
    var chart = chartBox();
    top.appendChild(chart);
    screen.appendChild(top);
    screen.appendChild(route());
    drawChart(chart);
  }

  function load() {
    var text = null;
    try {
      text = window.CrossoverTv ? window.CrossoverTv.view() : null;
    } catch (e) {
      text = null;
    }
    if (text) return Promise.resolve(text);
    return fetch('view.json').then(function (r) { return r.ok ? r.text() : null; }).catch(function () { return null; });
  }

  function start() {
    load().then(function (text) {
      try {
        view = text ? JSON.parse(text) : null;
      } catch (e) {
        view = null;
      }
      if (view && view.kind !== 'crossover-tv') view = null;
      seen = view && view.goal.date ? recordView(view.goal.date) : { previous: null, fresh: false };
      var go = function () {
        render();
        seen.fresh = false;
      };
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(go);
      else go();
    });
  }

  function toggle() {
    hidden = !hidden;
    render();
  }

  // The app calls these: OK on the remote, and a new view from the laptop.
  window.crossoverToggle = toggle;
  window.crossoverReload = start;

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      toggle();
      e.preventDefault();
    }
  });
  start();
})();
