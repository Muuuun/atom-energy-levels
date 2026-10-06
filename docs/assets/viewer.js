// Interactive level diagram: hover to preview a line or a level, click to pin its card, wheel / drag / pinch to navigate.
(async function () {
  const stage = document.getElementById('stage');
  const info = document.getElementById('info');
  const [svgText, data] = await Promise.all([
    fetch('diagram.svg').then(r => r.text()),
    fetch('data.json').then(r => r.json()),
  ]);
  stage.querySelector('.loading').remove();
  stage.insertAdjacentHTML('afterbegin', svgText.slice(svgText.indexOf('<svg')));
  const svg = stage.querySelector('svg');
  svg.removeAttribute('width');
  svg.removeAttribute('height');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', document.querySelector('h1').textContent);
  const T = data.transitions, L = data.levels;
  const linesOf = L.map(() => []);
  T.forEach((t, i) => { linesOf[t.lower].push(i); if (t.upper != null) linesOf[t.upper].push(i); });

  // ---------- formatting
  const TIER = { exp: 'measured', nist: 'NIST', theory: 'theory', model: 'model calc.' };
  const badge = t => t && TIER[t] ? '<span class="tier ' + t + '">' + TIER[t] + '</span>' : '';
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const upName = t => t.upper != null ? L[t.upper].html : t.upper_html;
  const lvBtn = k => '<button type="button" data-lv="' + k + '" title="Show this level">' + L[k].html + '</button>';
  const fd = d => d >= 10 ? d.toFixed(2) : d >= 0.1 ? d.toFixed(3) : d.toPrecision(3);
  const fA = a => { const e = Math.floor(Math.log10(a)); return (a / 10 ** e).toFixed(2) + ' × 10<sup>' + e + '</sup>'; };
  const ftau = ns => ns < 1e3 ? +ns.toPrecision(4) + ' ns' : ns < 1e6 ? +(ns / 1e3).toPrecision(4) + ' µs'
    : ns < 1e9 ? +(ns / 1e6).toPrecision(4) + ' ms' : +(ns / 1e9).toPrecision(4) + ' s';
  const colorOf = i => { const p = svg.querySelector('#tr-' + i + ' path'); return p ? p.style.stroke || p.style.fill : '#888'; };
  const row = (k, v) => '<tr><td>' + k + '</td><td>' + v + '</td></tr>';
  const SRC = data.sources || {};
  function cite(s) {  // citation text, linked to the page the number was read on
    if (!s) return '';
    let url = s.startsWith('NIST ASD') ? 'https://physics.nist.gov/asd' : '', best = '';
    for (const k in SRC) if (s.startsWith(k) && k.length > best.length) { best = k; url = SRC[k]; }
    return url ? '<a href="' + url + '" target="_blank" rel="noopener">' + esc(s) + '</a>' : esc(s);
  }
  const src = (label, s) => s ? '<div class="note"><b>' + label + ':</b> ' + cite(s) + '</div>' : '';

  function transitionCard(i) {
    const t = T[i];
    let h = '<h3><span class="swatch" style="background:' + colorOf(i) + '"></span>' + lvBtn(t.lower) + ' → ' +
            (t.upper != null ? lvBtn(t.upper) : t.upper_html) + '</h3>';
    if (t.kind === 'rydberg') h += '<div class="tag">Rydberg excitation, shown for n = 70</div>';
    if (t.kind === 'forbidden') h += '<div class="tag">Forbidden line (not electric-dipole allowed)</div>';
    if (t.use) h += '<div class="tag">' + esc(t.use) + '</div>';
    h += '<table>' + row('Wavelength (vacuum)', t.lam.toFixed(t.kind === 'rydberg' ? 3 : 4) + ' nm');
    if (t.air) h += row('Wavelength (air)', t.air.toFixed(4) + ' nm');
    h += row('Frequency' + badge(t.freq_tier), t.freq + ' THz');
    if (t.wn) h += row('Wavenumber', t.wn.toFixed(3) + ' cm⁻¹');
    if (t.limit_nm) h += row('Series limit (n → ∞)', t.limit_nm.toFixed(3) + ' nm');
    if (t.d != null) h += row('|⟨J‖er‖J′⟩|' + badge(t.d_tier), fd(t.d) + ' ea₀');
    if (t.kind === 'rydberg' && t.d_arc != null) h += row('|⟨J‖er‖J′⟩| (ARC)', fd(t.d_arc) + ' ea₀');
    if (t.A != null) h += row('Einstein A' + badge(t.A_tier), fA(t.A) + ' s⁻¹');
    if (t.br != null) h += row('Branching from upper level', (t.br * 100).toPrecision(3) + ' %');
    if (t.gamma_MHz != null) h += row('Upper-level linewidth Γ/2π', +t.gamma_MHz.toPrecision(4) + ' MHz');
    for (const [pair, s] of Object.entries(t.isotope_shifts || {}))
      h += row('Isotope shift ' + pair, s.value + (s.unc ? ' ± ' + s.unc : '') + ' MHz');
    h += '</table>';
    if (t.uncertain) h += '<div class="note">' + (t.kind === 'rydberg' ? 'Two calculations differ by about 2× on this line: order of magnitude only.' : 'This value is a bound or an estimate, not a direct measurement.') + '</div>';
    h += src(t.d != null ? 'Matrix element / A' : 'A', t.d_src || t.A_src);
    if (t.freq_tier === 'exp') h += src('Frequency', t.freq_src);
    if (t.br_src) h += src('Branching', t.br_src);
    for (const [pair, s] of Object.entries(t.isotope_shifts || {})) h += src('Isotope shift ' + pair, s.src);
    return h;
  }

  function levelCard(k) {
    const l = L[k];
    const rows = linesOf[k].slice().sort((a, b) => T[a].lam - T[b].lam).map(i => {
      const t = T[i], other = t.lower === k ? '→ ' + upName(t) : '← ' + L[t.lower].html;
      return '<tr class="row" data-i="' + i + '"><td><span class="swatch" style="background:' + colorOf(i) + '"></span>' + other +
             '</td><td>' + t.lam.toFixed(3) + '</td><td>' + (t.d != null ? fd(t.d) : '–') + '</td></tr>';
    }).join('');
    let h = '<h3>' + l.html + '</h3><table>' + row('Energy' + (l.E_tier ? badge(l.E_tier) : ''), l.E.toFixed(3) + ' cm⁻¹');
    if (l.E_nist != null) h += row('NIST energy', l.E_nist.toFixed(3) + ' cm⁻¹');
    if (l.tau_tier === 'stable') h += row('Lifetime', 'stable');
    else if (l.tau_ns != null) h += row('Lifetime' + badge(l.tau_tier), (l.tau_bound ? l.tau_bound + ' ' : '') + ftau(l.tau_ns) + (l.tau_unc ? ' ± ' + ftau(l.tau_unc) : ''));
    if (l.g != null) h += row('Landé g<sub>J</sub>', l.g + (l.g_tier === 'theory' ? ' (theory)' : ''));
    if (l.hfs) h += row('Hyperfine A', l.hfs.A + ' MHz') + (l.hfs.B ? row('Hyperfine B', l.hfs.B + ' MHz') : '');
    h += '</table><table class="lines" style="margin-top:8px"><tr><th>' + linesOf[k].length +
         ' lines</th><th>λ vac (nm)</th><th>d (ea₀)</th></tr>' + rows + '</table>';
    return h + src('Energy', l.E_src) + src('Lifetime', l.tau_src) + src('Hyperfine', l.hfs && l.hfs.src);
  }

  const helpCard = '<h3>How to read this</h3><div class="note" style="margin-top:0;font-size:13.5px;color:inherit">' +
    'Each arrow is a transition, labelled with its vacuum wavelength and reduced dipole matrix element.<br><br>' +
    'Point at an arrow, its label, or a level to fade everything else.<br><br>' +
    'Click to pin it: the card then stays put, so you can move to it, follow its sources, or pick a line from a level’s list. ' +
    'Release with ×, Esc, or a click on empty space.</div>';

  // ---------- selection
  // `pinned` owns the card and changes on clicks only. `hover` (what the pointer rests on in the diagram) borrows the card
  // only while nothing is pinned, and `rowHover` (a line of a level card's list) never touches it: hovering only changes
  // what the diagram emphasises, so the pointer can cross other lines on its way to a pinned card and then use it.
  let pinned = null, hover = null, rowHover = null, trail = [], cardKey, paintKey;
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const linesFor = s => !s ? [] : s.type === 'tr' ? [s.i] : linesOf[s.i];
  const nameOf = s => s.type === 'tr' ? L[T[s.i].lower].html + ' → ' + upName(T[s.i]) : L[s.i].html;
  function paint() {
    const sel = pinned || hover;
    let strong = linesFor(sel), soft = [];
    if (rowHover != null) { soft = strong; strong = [rowHover]; }  // one line out of the level's list
    else if (pinned && hover) soft = linesFor(hover);              // a glance at something else next to the pinned selection
    const key = JSON.stringify([!!sel, strong, soft]);
    if (key === paintKey) return;
    paintKey = key;
    svg.querySelectorAll('.hl, .sf').forEach(e => e.classList.remove('hl', 'sf'));
    svg.classList.toggle('dim', !!sel);
    for (const [ids, cls] of [[soft, 'sf'], [strong, 'hl']]) for (const i of ids) for (const p of ['tr-', 'trl-']) {
      const e = svg.getElementById(p + i);
      if (!e) continue;
      e.classList.remove('sf');
      e.classList.add(cls);
      if (p === 'trl-') e.parentNode.appendChild(e);  // label on top of its neighbours
    }
  }
  function card() {  // rewritten only when its owner changes, so a pinned card keeps its scroll position and text selection
    const sel = pinned || hover, key = JSON.stringify([sel, !!pinned, trail.length]);
    if (key === cardKey) return;
    cardKey = key;
    rowHover = null;
    info.classList.toggle('pinned', !!pinned);
    if (!sel) { info.innerHTML = helpCard; return; }
    const back = trail.length ? '<button type="button" data-act="back" title="Back">‹ ' + nameOf(trail[trail.length - 1]) + '</button>'
      : '<span>Pinned</span>';
    const bar = !pinned ? '<span>Preview · click to pin</span>' : back +
      '<button type="button" class="close" data-act="close" title="Release (Esc)" aria-label="Release the pinned selection">×</button>';
    info.innerHTML = '<div class="bar">' + bar + '</div>' + (sel.type === 'tr' ? transitionCard(sel.i) : levelCard(sel.i));
    info.scrollTop = 0;
  }
  const render = () => { card(); paint(); };
  function target(e) {
    for (let n = e.target; n && n !== svg; n = n.parentNode) {
      const m = n.id && n.id.match(/^(hit|tr|trl|lv|lvn|lvd)-(\d+)$/);
      if (m) return { type: m[1].startsWith('lv') ? 'lv' : 'tr', i: +m[2] };
    }
    return null;
  }
  let drag = null, moved = 0;
  svg.addEventListener('pointerover', e => { if (e.pointerType !== 'touch' && !drag) { hover = target(e); render(); } });
  svg.addEventListener('pointerleave', e => {  // a preview survives a move straight from its line into the card
    if (pinned || !(e.relatedTarget && info.contains(e.relatedTarget))) hover = null;
    render();
  });
  info.addEventListener('pointerover', e => {
    if (e.pointerType === 'touch') return;
    const r = e.target.closest('tr.row');
    rowHover = r ? +r.dataset.i : null;
    paint();
  });
  info.addEventListener('pointerleave', () => { rowHover = hover = null; render(); });
  info.addEventListener('click', e => {  // moving on from inside the card keeps a way back
    const act = e.target.closest('[data-act]'), r = e.target.closest('tr.row'), lv = e.target.closest('[data-lv]');
    const cur = pinned || hover, to = r ? { type: 'tr', i: +r.dataset.i } : lv ? { type: 'lv', i: +lv.dataset.lv } : null;
    if (act) { pinned = act.dataset.act === 'back' ? trail.pop() : null; if (!pinned) trail = []; }
    else if (String(getSelection())) return;  // the click that ends a text selection
    else if (to) { if (cur && !same(cur, to)) trail.push(cur); pinned = to; }
    else if (cur) pinned = cur;
    else return;
    hover = null;
    render();
  });
  window.addEventListener('keydown', e => { if (e.key === 'Escape' && pinned) { pinned = null; trail = []; render(); } });
  render();

  // ---------- filter by transition type (E1, intercombination, M1, E2, M2, Rydberg ...)
  const typeOf = t => t.kind === 'rydberg' ? 'Rydberg' : (t.type || 'E1');
  const types = [...new Set(T.map(typeOf))];
  const hidden = new Set();
  const filters = document.getElementById('filters');
  if (types.length > 1) {
    filters.innerHTML = '<span>Show</span>' + types.map(ty =>
      '<button type="button" aria-pressed="true" data-type="' + ty + '">' + ty + ' <small>' + T.filter(t => typeOf(t) === ty).length + '</small></button>').join('');
    filters.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b) return;
      const ty = b.dataset.type, on = hidden.has(ty);
      if (on) hidden.delete(ty); else hidden.add(ty);
      b.setAttribute('aria-pressed', String(on));
      T.forEach((t, i) => {
        if (typeOf(t) !== ty) return;
        for (const p of ['tr-', 'trl-', 'hit-']) { const el = svg.getElementById(p + i); if (el) el.style.display = on ? '' : 'none'; }
      });
    });
  }

  // ---------- pan and zoom on the viewBox
  const full = svg.viewBox.baseVal;
  const home = { x: full.x, y: full.y, w: full.width, h: full.height };
  let vb = { ...home };
  const setVB = () => svg.setAttribute('viewBox', vb.x + ' ' + vb.y + ' ' + vb.w + ' ' + vb.h);
  const toSvg = (cx, cy) => new DOMPoint(cx, cy).matrixTransform(svg.getScreenCTM().inverse());
  function zoomAt(cx, cy, f) {
    const w = Math.min(home.w * 1.2, Math.max(home.w / 60, vb.w * f));
    f = w / vb.w;
    const p = toSvg(cx, cy);
    vb = { x: p.x - (p.x - vb.x) * f, y: p.y - (p.y - vb.y) * f, w, h: vb.h * f };
    setVB();
  }
  const centre = () => { const r = stage.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
  stage.addEventListener('wheel', e => {
    if (e.target.closest('#info')) return;
    e.preventDefault();
    zoomAt(e.clientX, e.clientY, Math.exp(Math.max(-60, Math.min(60, e.deltaY)) * (e.ctrlKey ? 0.012 : 0.004)));
  }, { passive: false });
  document.getElementById('zin').onclick = () => zoomAt(...centre(), 1 / 1.5);
  document.getElementById('zout').onclick = () => zoomAt(...centre(), 1.5);
  document.getElementById('zfit').onclick = () => { vb = { ...home }; setVB(); };

  const pointers = new Map();
  svg.addEventListener('pointerdown', e => {
    pointers.set(e.pointerId, e);
    if (pointers.size === 1) { drag = { x: e.clientX, y: e.clientY }; moved = 0; }
  });
  window.addEventListener('pointermove', e => {
    if (!pointers.has(e.pointerId)) return;
    if (pointers.size === 2) {  // pinch
      const [a, b] = [...pointers.values()];
      const d0 = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      pointers.set(e.pointerId, e);
      const [c, d] = [...pointers.values()];
      const d1 = Math.hypot(c.clientX - d.clientX, c.clientY - d.clientY);
      if (d0 > 0 && d1 > 0) zoomAt((c.clientX + d.clientX) / 2, (c.clientY + d.clientY) / 2, d0 / d1);
      moved = 99;
      return;
    }
    pointers.set(e.pointerId, e);
    if (!drag) return;
    const slop = e.pointerType === 'touch' ? 10 : 5;  // a click may wobble by a few pixels without becoming a drag
    if (!moved && Math.hypot(e.clientX - drag.x, e.clientY - drag.y) < slop) return;
    moved = 99;
    stage.classList.add('dragging');
    const p0 = toSvg(drag.x, drag.y), p1 = toSvg(e.clientX, e.clientY);
    vb.x -= p1.x - p0.x;
    vb.y -= p1.y - p0.y;
    drag = { x: e.clientX, y: e.clientY };
    setVB();
  });
  window.addEventListener('pointerup', e => {
    if (!pointers.delete(e.pointerId)) return;
    stage.classList.remove('dragging');
    if (!moved) {  // a click, not a drag: pin or release
      const t = target(e);
      pinned = t && same(t, pinned) ? null : t;
      trail = [];
      render();
    }
    drag = null;
  });
  window.addEventListener('pointercancel', e => { pointers.delete(e.pointerId); drag = null; });
})();
