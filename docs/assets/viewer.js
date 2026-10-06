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

  // ---------- closed-transition check (cycling.py): leak per scattered photon and where it goes
  const sci = x => { const [m, e] = x.toExponential(2).split('e'); return +m + ' × 10<sup>' + String(+e).replace('-', '−') + '</sup>'; };
  const fshare = x => x >= 1e-3 ? +(x * 100).toPrecision(3) + ' %' : sci(x);
  const fcount = n => n < 100 ? String(+n.toPrecision(2)) : n < 1e6 ? Math.round(n).toLocaleString('en-US') : sci(n);
  const flam = nm => nm < 1e4 ? +nm.toPrecision(4) + ' nm' : nm < 1e7 ? +(nm / 1e3).toPrecision(3) + ' µm' : +(nm / 1e6).toPrecision(3) + ' mm';
  const mark = (s, tier) => (tier === 'model' ? '≈ ' : '') + s + (tier === 'theory' ? '*' : '');  // same marks as on the diagram
  const lvRef = r => r.lv != null ? lvBtn(r.lv) : r.html;
  const FROM = { exp: 'from measured data', nist: 'from NIST data', theory: 'from theory', model: 'from model calc.' };
  const derived = t => FROM[t] ? '<span class="tier ' + t + '">' + FROM[t] + '</span>' : '';  // a derived number is never tagged "measured"
  function cycleCard(t) {
    const c = t.cyc;
    if (!c) return '';
    const lo = L[t.lower].html, up = L[t.upper].html, s = n => n > 1 ? 's' : '';
    const paths = c.open ? c.open.map(r => lvRef(r) + ' (' + flam(r.lam) + ')').join(', ') + (c.n_open > c.open.length ? ', …' : '') : '';
    let h = '<div class="cyc"><h4>Closed-transition check</h4>', notes = [];
    if (c.cls === 'closed') {
      h += '<p><b>Closed</b> for electric-dipole decay: ' + lo + ' is the only level below ' + up + ' that such a decay can reach.</p>';
    } else if (c.cls === 'open') {
      h += '<p><b>Not closed</b>: an electric-dipole decay of ' + up + ' can also reach ' + c.n_open + ' other level' + s(c.n_open) +
           ', and no rate is known that would give the size of the leak.</p>';
      notes.push('Possible decay path' + s(c.n_open) + ': ' + paths + '.');
    } else {
      h += '<table>' + row('Leak per photon' + derived(c.tier), (c.bound ? '≥ ' : '') + fshare(c.leak)) +
           row('Photons scattered before a leak', (c.bound ? '≤ ' : '') + fcount(c.n)) + '</table>';
      if (c.ch.length) h += '<table class="lines"><tr><th>Leaks to</th><th>λ</th><th>Share</th></tr>' + c.ch.map(r =>
        '<tr><td>' + lvRef(r) + (r.dark ? '<span class="dark" title="No electric-dipole decay from this level: the atom stays there until it is repumped">long-lived</span>' : '') +
        '</td><td>' + flam(r.lam) + '</td><td>' + mark(fshare(r.f), r.tier) + '</td></tr>').join('') + '</table>';
      if (c.more) notes.push(c.more + ' weaker decay line' + s(c.more) + ' not shown.');
      if (c.basis === 'direct') notes.push('Leak = 1 − branching ratio of this line.' +
        (c.ch_sum ? ' The decay lines listed above add up to ' + mark(fshare(c.ch_sum), c.ch_tier) + '.' : ''));
      else notes.push(c.basis === 'lifetime' ? 'Leak = sum of the other decay lines of ' + up + ' (rate × lifetime).'
        : 'Leak = share of the other lines in the sum of the listed rates (no lifetime measured for ' + up + ').');
      if (c.bound) notes.push('Lower limit: ' + c.n_open + ' more possible decay path' + s(c.n_open) + ' without a listed rate (' + paths + ').');
      if (c.ch.some(r => r.tier === 'theory' || r.tier === 'model') || c.ch_tier === 'theory' || c.ch_tier === 'model') notes.push('* theory, ≈ model calculation.');
    }
    if (c.lower === 'decays') notes.push('The lower level ' + lo + ' decays itself, so this line cannot cycle on its own.');
    if (c.cls !== 'open') notes.push('While this line is pinned, wavy arrows in the diagram show the decay channels of ' + up + ' with their share.');
    return h + (notes.length ? '<div class="note">' + notes.join(' ') + '</div>' : '') +
      '<div class="note">Derived from the data of this page, not measured as such. Fine structure only: hyperfine and Zeeman dark states are not considered.</div></div>';
  }

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
    h += cycleCard(t);
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
  // ---------- decay channels of the pinned line's upper level: wavy arrows (spontaneous emission) labelled with their share
  const decay = svg.appendChild(document.createElementNS('http://www.w3.org/2000/svg', 'g'));
  decay.id = 'decay';
  const lineOf = {};
  T.forEach((t, i) => { if (t.upper != null) lineOf[t.lower + '>' + t.upper] = i; });
  const ends = id => {  // the two end points of a level bar or of a line (lower end first)
    const p = svg.querySelector('#' + id + ' path');
    if (!p) return null;
    const n = p.getAttribute('d').match(/-?[\d.]+/g).map(Number);
    return [[n[0], n[1]], [n[2], n[3]]];
  };
  const clamp = (x, a, b) => Math.min(Math.max(x, a), b);
  const sup = s => s.replace(/<sup>(.*?)<\/sup>/g, (m, e) => e.replace(/./g, ch => ch === '−' ? '⁻' : '⁰¹²³⁴⁵⁶⁷⁸⁹'[ch]));  // SVG text has no <sup>
  const fkept = x => x > 0.999 && x < 1 ? +(x * 100).toFixed(Math.min(8, Math.ceil(-Math.log10((1 - x) * 100)) + 1)) + ' %' : +(x * 100).toPrecision(3) + ' %';
  function wavy(S, E, color, g) {  // g: size factor (user units per screen pixel). Returns the arrow and where a label can sit
    const dx = E[0] - S[0], dy = E[1] - S[1], len = Math.hypot(dx, dy);
    if (len < 12) return null;
    const u = [dx / len, dy / len], n = [-u[1], u[0]], head = Math.min(11 * g, len / 3), body = len - head - 2;
    const waves = Math.max(1, Math.round(body / (13 * g))), a = Math.min(4.2 * g, body / 6), pts = [], f = p => p[0].toFixed(1) + ' ' + p[1].toFixed(1);
    for (let k = 0; k <= waves * 12; k++) {
      const s = body * k / (waves * 12), w = a * Math.min(1, s / (5 * g), (body - s) / (5 * g)) * Math.sin(2 * Math.PI * k / 12);
      pts.push(f([S[0] + u[0] * s + n[0] * w, S[1] + u[1] * s + n[1] * w]));
    }
    const B = [E[0] - u[0] * head, E[1] - u[1] * head], hw = head * 0.4, d = 'M' + pts.join('L') + 'L' + f(B);
    const tip = [E, [B[0] + n[0] * hw, B[1] + n[1] * hw], [B[0] - n[0] * hw, B[1] - n[1] * hw]].map(f).join(' ');
    return { svg: '<path class="halo" d="' + d + '"/><path d="' + d + '" style="stroke:' + color + '"/><polygon points="' + tip + '" style="fill:' + color + '"/>',
             at: (t, side) => [S[0] + dx * t + n[0] * side * (a + 13 * g), S[1] + dy * t + n[1] * side * (a + 13 * g)] };
  }
  let decayKey = null;
  function decayArrows() {
    const i = pinned && pinned.type === 'tr' ? pinned.i : null, c = i != null && T[i].cyc;
    // drawn at a constant size on screen until the diagram is zoomed in to its own scale, so the shares can be read in the full view
    const m = c && c.cls !== 'open' && svg.getScreenCTM(), g = m ? +clamp(1 / m.a, 1, 5).toFixed(1) : 1, key = m ? i + '@' + g : null;
    if (key === decayKey) return;
    decayKey = key;
    decay.innerHTML = '';
    if (key == null) return;
    decay.style.setProperty('--g', g);
    const t = T[i], U = ends('lv-' + t.upper);
    // back to the lower level: what the leak leaves over; then the other decay lines that end on a drawn level
    const chans = [{ lv: t.lower, label: c.cls === 'closed' ? '100 %' : (c.bound ? '≤ ' : '') + fkept(1 - c.leak) }]
      .concat((c.ch || []).filter(r => r.lv != null).map(r => ({ lv: r.lv, label: mark(fshare(r.f), r.tier) })));
    let h = '', texts = '';
    const boxes = [], fs = 12.5 * g;
    for (const ch of chans) {
      const j = lineOf[ch.lv + '>' + t.upper], line = j != null && ends('hit-' + j), D = ends('lv-' + ch.lv);
      if (!U || !D) continue;
      let S, E, shift = 0;
      if (line) {  // next to the straight arrow of the drawn line, at a constant distance from it
        E = line[0]; S = line[1];
        const d = clamp(14 * g * Math.hypot(E[0] - S[0], E[1] - S[1]) / Math.abs(E[1] - S[1]), 14 * g, 40 * g);
        const right = Math.min(U[1][0] - S[0], D[1][0] - E[0]), left = Math.min(S[0] - U[0][0], E[0] - D[0][0]);  // room on the two level bars
        shift = right >= left ? Math.min(d, Math.max(right, 0)) : -Math.min(d, Math.max(left, 0));
      } else {     // a line that is not drawn (beyond 2 µm, or too weak for the diagram)
        S = [clamp((D[0][0] + D[1][0]) / 2, U[0][0] + 8, U[1][0] - 8), U[0][1]];
        E = [clamp((U[0][0] + U[1][0]) / 2, D[0][0] + 8, D[1][0] - 8), D[0][1]];
      }
      const arrow = wavy([S[0] + shift, S[1]], [E[0] + shift, E[1]], line ? colorOf(j) : '#666', g);
      if (!arrow) continue;
      h += arrow.svg;
      // label: on the far side of the straight arrow if it fits there, at the first place that is clear of the labels already set
      const text = sup(ch.label), far = shift && (S[1] - E[1]) * shift > 0 ? 1 : -1, w = fs * 0.31 * text.length + 2 * g, hh = fs * 0.65;
      let box = null;
      search: for (const side of [far, -far]) for (const at of [0.5, 0.34, 0.66, 0.24, 0.76, 0.42, 0.58]) {
        const p = arrow.at(at, side), b = [p[0] - w, p[1] - hh, p[0] + w, p[1] + hh];
        if (!box) box = b;  // nothing is clear: the first choice
        if (!boxes.some(o => b[0] < o[2] && b[2] > o[0] && b[1] < o[3] && b[3] > o[1])) { box = b; break search; }
      }
      boxes.push(box);
      texts += '<text x="' + ((box[0] + box[2]) / 2).toFixed(1) + '" y="' + ((box[1] + box[3]) / 2).toFixed(1) + '">' + text + '</text>';
    }
    h += texts;  // above every arrow
    decay.innerHTML = h;
  }
  const render = () => { card(); paint(); decayArrows(); };
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
  const setVB = () => { svg.setAttribute('viewBox', vb.x + ' ' + vb.y + ' ' + vb.w + ' ' + vb.h); decayArrows(); };
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
