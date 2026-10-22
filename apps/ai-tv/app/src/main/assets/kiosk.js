// Injected into every page AI TV shows. It makes the sites work on the TV's
// Chrome 98 WebView, takes the remote's commands from the app and reports what
// is on screen. It runs once per document.
(() => {
  if (window.soyKiosk) return;
  window.soyKiosk = true;

  // Chrome 98 drops every rule inside @layer, where Tailwind 4 sites keep all
  // of their styles, and has no dvh units. Each stylesheet is fetched again and
  // added with the layer wrappers removed, url()s made absolute and dvh mapped
  // to vh. Source order keeps the layer order.
  const unlayer = (css) => {
    const parts = [];
    const stack = [];
    let from = 0;
    let i = 0;
    const n = css.length;
    while (i < n) {
      const c = css.charCodeAt(i);
      if (c === 34 || c === 39) {
        let j = i + 1;
        while (j < n && css.charCodeAt(j) !== c) j += css.charCodeAt(j) === 92 ? 2 : 1;
        i = j + 1;
      } else if (c === 47 && css.charCodeAt(i + 1) === 42) {
        const j = css.indexOf('*/', i + 2);
        i = j < 0 ? n : j + 2;
      } else if (c === 64 && css.startsWith('@layer', i) && !/[\w-]/.test(css[i + 6] || '')) {
        let j = i + 6;
        while (j < n && css[j] !== '{' && css[j] !== ';') j++;
        parts.push(css.slice(from, i));
        if (css[j] === '{') stack.push(true);
        i = j + 1;
        from = i;
      } else if (c === 123) {
        stack.push(false);
        i++;
      } else if (c === 125) {
        if (stack.pop()) {
          parts.push(css.slice(from, i));
          from = i + 1;
        }
        i++;
      } else {
        i++;
      }
    }
    parts.push(css.slice(from));
    return parts.join('');
  };
  const fix = (css, base) => unlayer(css)
    .replace(/url\(\s*(['"]?)([^'")]+)\1\s*\)/g, (all, quote, ref) =>
      /^(data:|https?:|#)/.test(ref) ? all : 'url("' + new URL(ref, base).href + '")')
    .replace(/(\d)[dsl]v(h|w|min|max)\b/g, '$1v$2');
  let pending = 0;
  const done = new Set();
  const load = (link) => {
    const href = link.href;
    if (!href || done.has(href)) return;
    done.add(href);
    pending++;
    fetch(href)
      .then((response) => response.text())
      .then((css) => {
        const style = document.createElement('style');
        style.textContent = fix(css, href);
        link.after(style);
      })
      .catch(() => {})
      .finally(() => pending--);
  };
  const scan = () => document.querySelectorAll('link[rel="stylesheet"]').forEach(load);
  scan();
  new MutationObserver(scan).observe(document.head, { childList: true });

  const text = (e) => (e.innerText || '').replace(/\s+/g, ' ').trim();
  const shown = (e) => !!e && e.getClientRects().length > 0;
  const buttons = () => [...document.querySelectorAll('button')];
  const css = (rules) => {
    const style = document.createElement('style');
    style.textContent = rules;
    document.head.appendChild(style);
  };
  const playing = () =>
    [...document.querySelectorAll('video')].find((v) => !v.paused && v.readyState >= 2);

  let page = { ok() {}, step() {}, name: () => '', gate: () => false, tick() {} };

  if (location.hostname === 'fal.live') {
    // Mouse-only controls; the remote and the TV's own volume replace them.
    css('button[aria-label="Open menu"],button[aria-label^="Turn sound"]{display:none!important}');
    const consent = () => {
      const dialog = document.querySelector('dialog[open]');
      return dialog && [...dialog.querySelectorAll('button')].find((b) => text(b) === 'Enter');
    };
    // The sidebar's channel buttons, without the password-protected ones.
    const channels = () => buttons().filter((b) =>
      /\d+\s*watching/.test(text(b)) && !/password/i.test(text(b)));
    const nameOf = (b) => text(b).replace(/\s*\d+\s*watching.*$/, '');
    const current = () => {
      const b = document.querySelector('button[aria-label^="Channel: "]');
      return b ? b.getAttribute('aria-label').replace(/^Channel: /, '').replace(/\. Change channel$/, '') : '';
    };
    page = {
      // OK on the age and terms dialog is the viewer pressing its Enter button.
      ok() {
        const b = consent();
        if (b) b.click();
      },
      step(n) {
        const list = channels();
        if (!list.length) return;
        const i = list.map(nameOf).indexOf(current());
        list[(i + n + list.length) % list.length].click();
      },
      name: current,
      gate: () => !!consent(),
      // Sound is a player setting, not a terms prompt, so it starts as soon as
      // the site offers it.
      tick() {
        if (consent()) return;
        const b = buttons().find((x) => text(x) === 'Enter with sound' && shown(x));
        if (b) b.click();
      },
    };
  } else if (location.hostname === 'labs.google') {
    // Flow TV plays one clip at a time in a framed player: show only the video.
    css('body.soy-stage *{visibility:hidden!important}'
      + 'body.soy-stage video.soy-main{visibility:visible!important;position:fixed!important;'
      + 'inset:0!important;width:100vw!important;height:100vh!important;max-width:none!important;'
      + 'max-height:none!important;z-index:2147483000!important;background:#000!important;'
      + 'object-fit:contain!important;border-radius:0!important}'
      + '.soy-up{transform:none!important;filter:none!important;backdrop-filter:none!important;'
      + 'perspective:none!important;contain:none!important;will-change:auto!important}');
    const link = (label) => document.querySelector('a[aria-label="' + label + '"]');
    page = {
      ok() {},
      step(n) {
        const a = link(n > 0 ? 'Go to next channel' : 'Go to previous channel');
        if (a) a.click();
      },
      name: () => document.title.split(' | ')[1] || '',
      gate: () => false,
      tick() {
        const v = playing() || document.querySelector('video');
        if (!v) return;
        document.querySelectorAll('video.soy-main').forEach((e) => {
          if (e !== v) e.classList.remove('soy-main');
        });
        v.classList.add('soy-main');
        for (let e = v.parentElement; e && e !== document.body; e = e.parentElement) {
          e.classList.add('soy-up');
        }
        document.body.classList.add('soy-stage');
        const unmute = document.querySelector('button[aria-label="Unmute video"]');
        if (unmute) unmute.click();
      },
    };
  }

  // Reload when a video that was playing stops moving for 90 seconds, at most
  // every ten minutes so a site that is down is not hammered.
  let last = -1;
  let still = 0;
  setInterval(() => {
    const v = document.querySelector('video.soy-main') || document.querySelector('video');
    if (!v || !(v.currentTime > 0)) {
      last = -1;
      still = 0;
      return;
    }
    still = v.currentTime === last ? still + 5 : 0;
    last = v.currentTime;
    if (still < 90 || document.hidden) return;
    const at = Number(sessionStorage.getItem('soyReload') || 0);
    if (Date.now() - at > 600000) {
      sessionStorage.setItem('soyReload', String(Date.now()));
      location.reload();
    }
  }, 5000);

  window.soyOk = () => page.ok();
  window.soyStep = (n) => page.step(n);
  window.soyTick = () => {
    page.tick();
    return JSON.stringify({
      ready: pending === 0,
      gate: page.gate(),
      playing: !!playing(),
      name: page.name(),
      url: location.href,
    });
  };
})();
