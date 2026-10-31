// ==UserScript==
// @name         YouTube Studio – export vybraných videí do CSV
// @namespace    https://studio.youtube.com/
// @version      0.6
// @description  Export vybraných Shorts: název, celý popis, datum+čas, zhlédnutí, délka, hashtagy, tagy + retence + zdroje návštěvnosti + zobrazení miniatury
// @match        https://studio.youtube.com/channel/*/videos/*
// @grant        GM_xmlhttpRequest
// @connect      www.youtube.com
// ==/UserScript==

(function () {
  'use strict';

  const DELIMITER = ';';              // české Excely: středník; pro čárku změň na ','
  const TIMEZONE = 'Europe/Prague';   // v jakém pásmu chceš datum a čas publikace
  const DECIMAL_COMMA = true;         // desetinná čárka (česká lokalizace Excelu); false = tečka
  const ANALYTICS_TIMEOUT_MS = 20000; // jak dlouho čekat na načtení analytiky jednoho videa

  // ---------- DOM ve Studiu ----------
  function pickText(root, selectors) {
    for (const sel of selectors) {
      const el = root.querySelector(sel);
      if (el && el.innerText && el.innerText.trim()) return el.innerText.trim();
    }
    return '';
  }

  function deepAll(root, out = []) {
    root.querySelectorAll('*').forEach((el) => {
      out.push(el);
      if (el.shadowRoot) deepAll(el.shadowRoot, out);
    });
    return out;
  }

  function isSelected(row) {
    for (const el of deepAll(row)) {
      const tag = el.tagName.toLowerCase();
      const looksLikeCheckbox =
        tag.includes('checkbox') ||
        el.getAttribute('role') === 'checkbox' ||
        (tag === 'input' && el.type === 'checkbox') ||
        el.hasAttribute('aria-checked');
      if (!looksLikeCheckbox) continue;
      if (
        el.checked === true ||
        el.getAttribute('aria-checked') === 'true' ||
        el.hasAttribute('checked') ||
        el.classList.contains('checked')
      ) return true;
    }
    return (
      row.hasAttribute('selected') ||
      row.hasAttribute('is-selected') ||
      row.classList.contains('selected')
    );
  }

  function parseRow(row) {
    const titleEl = row.querySelector('#video-title');
    const title = titleEl ? titleEl.innerText.trim() : '';
    const href = titleEl ? titleEl.getAttribute('href') || '' : '';
    const idMatch = href.match(/\/video\/([^/]+)/);
    const id = idMatch ? idMatch[1] : '';

    const listDescription = pickText(row, [
      '#description-container',
      '.description',
      '[class*="description"]',
    ]);
    const dateRaw = pickText(row, [
      '.tablecell-date',
      '[class*="tablecell-date"]',
      '.cell-body.date',
    ]);
    const views = pickText(row, [
      '.tablecell-views',
      '[class*="tablecell-views"]',
    ]).split('\n')[0];

    return {
      id,
      title,
      listDescription,
      listDate: dateRaw.split('\n')[0].trim(),
      listViews: views,
    };
  }

  // ---------- čisté pomocné funkce ----------
  function cleanNumber(s) {
    const t = String(s ?? '').replace(/[\s\u00a0\u202f]/g, '');
    return /^\d+$/.test(t) ? t : '';
  }

  function extractHashtags(text) {
    const found = String(text || '').match(/#[\p{L}\p{N}_]+/gu) || [];
    return found.filter((h) => !/^#\d+$/.test(h)); // YouTube ignoruje čistě číselné
  }

  function uniq(arr) {
    const seen = new Set();
    return arr.filter((x) => {
      const k = x.toLowerCase();
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
  }

  // "30. 10. 2026" -> "2026-10-30"
  function listDateToIso(s) {
    const m = String(s).match(/(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})/);
    return m ? `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}` : '';
  }

  function localParts(date) {
    const p = new Intl.DateTimeFormat('en-CA', {
      timeZone: TIMEZONE, hour12: false,
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    }).formatToParts(date).reduce((a, x) => ((a[x.type] = x.value), a), {});
    const hh = p.hour === '24' ? '00' : p.hour;
    return { date: `${p.year}-${p.month}-${p.day}`, time: `${hh}:${p.minute}` };
  }

  // Z HTML stránky videa vytáhne vše, co jde bez přihlášení do analytiky
  function parseWatchPage(html) {
    const out = {};

    const d = html.match(/"shortDescription":"((?:[^"\\]|\\.)*)"/);
    if (d) { try { out.description = JSON.parse('"' + d[1] + '"'); } catch (e) {} }

    const len = html.match(/"lengthSeconds":"(\d+)"/);
    if (len) out.lengthSeconds = len[1];

    const vc = html.match(/"viewCount":"(\d+)"/);
    if (vc) out.viewCount = vc[1];

    const kw = html.match(/"keywords":\[((?:[^\]\\]|\\.)*)\]/);
    if (kw) { try { out.keywords = JSON.parse('[' + kw[1] + ']'); } catch (e) {} }

    // publishDate/uploadDate: bereme ten, který obsahuje čas (T…)
    const dates = [html.match(/"publishDate":"([^"]+)"/), html.match(/"uploadDate":"([^"]+)"/)]
      .filter(Boolean).map((m) => m[1]);
    out.publishIso = dates.find((x) => x.includes('T')) || dates[0] || '';
    return out;
  }

  function fetchWatchPage(id) {
    return new Promise((resolve) => {
      if (!id) return resolve(null);
      GM_xmlhttpRequest({
        method: 'GET',
        url: `https://www.youtube.com/watch?v=${id}`,
        headers: { 'Accept-Language': 'cs-CZ,cs;q=0.9' },
        timeout: 20000,
        onload: (res) => resolve(parseWatchPage(res.responseText || '')),
        onerror: () => resolve(null),
        ontimeout: () => resolve(null),
      });
    });
  }

  // ---------- analytika (načtení stránky Studia ve skrytém iframu) ----------
  // Text stránky včetně shadow DOM, mezery sjednocené
  function deepText(root) {
    let out = '';
    const walk = (node) => {
      if (node.nodeType === 3) { out += node.nodeValue + ' '; return; }
      if (node.nodeType !== 1 && node.nodeType !== 11) return;
      if (node.tagName === 'SCRIPT' || node.tagName === 'STYLE') return;
      if (node.shadowRoot) walk(node.shadowRoot);
      for (const c of node.childNodes) walk(c);
    };
    walk(root);
    return out.replace(/[\s\u00a0\u202f]+/g, ' ');
  }

  function fmtNumber(s) {
    if (s === '' || s == null) return '';
    const t = String(s).replace(',', '.');
    return DECIMAL_COMMA ? t.replace('.', ',') : t;
  }

  function durToSeconds(d) {
    if (!d) return '';
    const parts = d.split(':').map(Number);
    return String(parts.reduce((a, x) => a * 60 + x, 0));
  }

  // Z textu stránky "Míra udržení publika" vytáhne tři metriky podle českých popisků
  function parseRetention(text) {
    const stayed = text.match(/(\d+(?:[.,]\d+)?) ?% ?Zůstali a sledovali/);
    const dur = text.match(/(\d+(?::\d{2}){1,2}) ?Průměrná doba sledování/);
    const pct = text.match(/(\d+(?:[.,]\d+)?) ?% ?Průměrná míra sledování/);
    return {
      stayed: stayed ? stayed[1] : '',
      avgDurSeconds: dur ? durToSeconds(dur[1]) : '',
      avgPct: pct ? pct[1] : '',
    };
  }

  // Generický loader: otevře stránku Studia ve skrytém iframu a čeká, až probe() najde data
  function loadFrame(url, probe) {
    return new Promise((resolve) => {
      const iframe = document.createElement('iframe');
      Object.assign(iframe.style, {
        position: 'fixed', left: '-10000px', top: '0',
        width: '1280px', height: '900px', opacity: '0', pointerEvents: 'none',
      });
      iframe.src = url;
      document.body.appendChild(iframe);

      const start = Date.now();
      let last = null, lastKey = '', stable = 0;
      const done = (r) => { clearInterval(timer); iframe.remove(); resolve(r); };
      const timer = setInterval(() => {
        let p = { result: null, complete: false };
        try { p = probe(iframe.contentDocument.body); } catch (e) {}
        if (p.result) last = p.result;
        if (p.complete) {
          const key = JSON.stringify(p.result);
          stable = key === lastKey ? stable + 1 : 0;
          lastKey = key;
          if (stable >= 2) return done(p.result); // data se 3× po sobě nezměnila
        } else { stable = 0; lastKey = ''; }
        if (Date.now() - start > ANALYTICS_TIMEOUT_MS) return done(last);
      }, 500);
    });
  }

  function loadRetention(id) {
    if (!id) return Promise.resolve(null);
    const url =
      `https://studio.youtube.com/video/${id}/analytics/tab-overview/period-default/explore` +
      `?entity_type=VIDEO&entity_id=${id}&time_period=lifetime&explore_type=AUDIENCE_RETENTION`;
    return loadFrame(url, (body) => {
      const r = parseRetention(deepText(body));
      const found = [r.stayed, r.avgDurSeconds, r.avgPct].filter((x) => x !== '').length;
      return { result: found ? r : null, complete: found === 3 };
    });
  }

  function loadTraffic(id) {
    if (!id) return Promise.resolve(null);
    const url =
      `https://studio.youtube.com/video/${id}/analytics/tab-overview/period-default/explore` +
      `?entity_type=VIDEO&entity_id=${id}&time_period=since_publish&explore_type=TABLE_AND_CHART` +
      `&metrics_computation_type=DELTA&metric=EXTERNAL_VIEWS&granularity=DAY` +
      `&t_metrics=EXTERNAL_VIEWS&t_metrics=EXTERNAL_WATCH_TIME&t_metrics=AVERAGE_WATCH_TIME` +
      `&t_metrics=VIDEO_THUMBNAIL_IMPRESSIONS&t_metrics=VIDEO_THUMBNAIL_IMPRESSIONS_VTR` +
      `&v_metrics=EXTERNAL_VIEWS&v_metrics=EXTERNAL_WATCH_TIME&v_metrics=SUBSCRIBERS_NET_CHANGE` +
      `&v_metrics=VIDEO_THUMBNAIL_IMPRESSIONS&v_metrics=VIDEO_THUMBNAIL_IMPRESSIONS_VTR` +
      `&dimension=TRAFFIC_SOURCE_TYPE&o_column=EXTERNAL_VIEWS&o_direction=ANALYTICS_ORDER_DIRECTION_DESC`;
    return loadFrame(url, (body) => {
      const t = parseTraffic(deepTokens(body));
      return { result: t, complete: !!t && t.rows.length > 0 };
    });
  }

  // ---------- tabulka "Zdroj návštěvnosti" ----------
  // Seznam textových uzlů stránky (včetně shadow DOM); každá buňka tabulky je zvlášť
  function deepTokens(root) {
    const out = [];
    const walk = (node) => {
      if (node.nodeType === 3) {
        const t = node.nodeValue.replace(/[\s\u00a0\u202f]+/g, ' ').trim();
        if (t) out.push(t);
        return;
      }
      if (node.nodeType !== 1 && node.nodeType !== 11) return;
      if (node.tagName === 'SCRIPT' || node.tagName === 'STYLE') return;
      if (node.shadowRoot) walk(node.shadowRoot);
      for (const c of node.childNodes) walk(c);
    };
    walk(root);
    return out;
  }

  const TRAFFIC_HEADER_LAST = 'Míra prokliku miniatury';
  const KNOWN_SOURCES = [
    'Feed videí Shorts', 'Jiné funkce YouTube', 'Stránky kanálu', 'Navrhovaná videa',
    'Playlisty', 'Přímé zadání nebo neznámý zdroj', 'Procházecí funkce',
  ];

  function isValueToken(t) {
    return /^[—–-]$/.test(t) ||
      /^\d[\d ]*(?:[.,]\d+)?(?: ?%)?$/.test(t) ||
      /^\d+:\d{2}(?::\d{2})?$/.test(t);
  }

  function toNum(t) {
    if (t == null || /^[—–-]$/.test(t)) return null;
    if (/^\d+:\d{2}/.test(t)) return Number(durToSeconds(t));
    const n = Number(t.replace(/[ %]/g, '').replace(',', '.'));
    return isNaN(n) ? null : n;
  }

  // Sloupce: Zhlédnutí | Doba sledování (hodiny) | Průměrná doba sledování | Zobrazení miniatury | Míra prokliku miniatury
  function parseTraffic(tokens) {
    let idx = -1;
    for (let k = 0; k < tokens.length - 1; k++) {
      if (tokens[k] === TRAFFIC_HEADER_LAST && tokens[k + 1] === 'Celkem') idx = k;
    }
    if (idx < 0) idx = tokens.lastIndexOf(TRAFFIC_HEADER_LAST);
    if (idx < 0) return null;

    const rows = [];
    let i = idx + 1;
    while (i < tokens.length) {
      const tok = tokens[i];
      if (isValueToken(tok)) { i++; continue; }
      const vals = [];
      let j = i + 1;
      while (j < tokens.length && vals.length < 5 && isValueToken(tokens[j])) vals.push(tokens[j++]);
      if (vals.length || tok === 'Celkem' || KNOWN_SOURCES.includes(tok)) {
        const n = vals.map(toNum);
        rows.push({
          label: tok,
          views: n[0] ?? null, watchH: n[1] ?? null, avgDurS: n[2] ?? null,
          impr: n[3] ?? null, ctr: n[4] ?? null,
        });
      }
      i = j;
    }
    const total = rows.find((r) => r.label === 'Celkem');
    if (!total || total.views === null) return null;
    return { total, rows: rows.filter((r) => r !== total) };
  }

  // Podíly zdrojů na zhlédnutích; "Ostatní" = vše, co není feed/vyhledávání/procházení/hashtagy
  function summarizeSources(t) {
    const T = t.total.views;
    const sumBy = (re) => t.rows.filter((r) => re.test(r.label)).reduce((a, r) => a + (r.views || 0), 0);
    const feed = sumBy(/feed.*shorts|shorts.*feed/i);
    const search = sumBy(/vyhled/i);
    const browse = sumBy(/proch[aá]z/i);
    const hashtag = sumBy(/hashtag/i);
    const other = Math.max(0, T - feed - search - browse - hashtag);
    const pct = (v) => (T > 0 ? fmtNumber(String(Math.round((v / T) * 1000) / 10)) : '');
    return {
      feed: pct(feed), search: pct(search), browse: pct(browse), hashtag: pct(hashtag), other: pct(other),
      all: t.rows.map((r) => `${r.label}=${r.views ?? ''}`).join(' | '),
    };
  }

  // ---------- sestavení řádku ----------
  function buildRecord(row, page, exportedAt, ret, traf) {
    const hasPage = !!(page && page.description !== undefined);
    const description = hasPage ? page.description : row.listDescription;

    // datum + čas publikace
    let pubDate = '', pubTime = '', pubMs = null;
    if (page && page.publishIso) {
      if (page.publishIso.includes('T')) {
        const dt = new Date(page.publishIso);
        if (!isNaN(dt)) {
          const lp = localParts(dt);
          pubDate = lp.date; pubTime = lp.time; pubMs = dt.getTime();
        }
      } else {
        pubDate = page.publishIso.slice(0, 10); // jen datum, čas není k dispozici
      }
    }
    if (!pubDate) pubDate = listDateToIso(row.listDate);

    const ageMs = pubMs !== null ? exportedAt - pubMs
      : pubDate ? exportedAt - new Date(pubDate + 'T00:00:00').getTime() : null;

    const views = cleanNumber(row.listViews) || (page && page.viewCount) || '';

    const tagsTitle = extractHashtags(row.title);
    const tagsDesc = extractHashtags(description);
    const src = traf ? summarizeSources(traf) : null;

    return {
      video_id: row.id,
      url: row.id ? `https://www.youtube.com/shorts/${row.id}` : '',
      nazev: row.title,
      popis: description,
      datum_publikace: pubDate,
      cas_publikace: pubTime,
      datum_exportu: localParts(new Date(exportedAt)).date,
      stari_dni: ageMs !== null ? Math.floor(ageMs / 86400000) : '',
      stari_hodin: pubMs !== null ? Math.floor(ageMs / 3600000) : '',
      zhlednuti: views,
      delka_s: page && page.lengthSeconds ? page.lengthSeconds : '',
      zustali_sledovali_pct: ret ? fmtNumber(ret.stayed) : '',
      prum_doba_sledovani_s: ret ? ret.avgDurSeconds : '',
      prum_mira_sledovani_pct: ret ? fmtNumber(ret.avgPct) : '',
      doba_sledovani_celkem_h: traf && traf.total.watchH !== null ? fmtNumber(String(traf.total.watchH)) : '',
      zobrazeni_miniatury: traf && traf.total.impr !== null ? String(traf.total.impr) : '',
      mira_prokliku_pct: traf && traf.total.ctr !== null ? fmtNumber(String(traf.total.ctr)) : '',
      zdroj_shorts_feed_pct: src ? src.feed : '',
      zdroj_vyhledavani_pct: src ? src.search : '',
      zdroj_prochazeni_pct: src ? src.browse : '',
      zdroj_hashtagy_pct: src ? src.hashtag : '',
      zdroj_ostatni_pct: src ? src.other : '',
      zdroje_vse: src ? src.all : '',
      hashtagy_nazev: tagsTitle.join(' '),
      hashtagy_popis: tagsDesc.join(' '),
      pocet_hashtagu: uniq([...tagsTitle, ...tagsDesc]).length,
      tagy_skryte: page && page.keywords ? page.keywords.join(', ') : '',
      popis_kompletni: hasPage ? 'ano' : 'NE',
      retence_nactena: ret && ret.stayed !== '' ? 'ano' : 'NE',
      zdroje_nactene: traf ? 'ano' : 'NE',
    };
  }

  // ---------- CSV ----------
  function cell(value) {
    const s = String(value ?? '');
    if (s === '') return '';                 // chybějící hodnota = prázdná buňka
    return s.includes(DELIMITER) || /["\r\n]/.test(s) || s !== s.trim()
      ? `"${s.replace(/"/g, '""')}"` : s;
  }

  function toCsv(records) {
    const cols = Object.keys(records[0]);
    const lines = [cols.join(DELIMITER)];
    for (const r of records) lines.push(cols.map((c) => cell(r[c])).join(DELIMITER));
    return lines.join('\r\n');
  }

  function download(filename, text) {
    const blob = new Blob(['\uFEFF' + text], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }

  // ---------- hlavní akce ----------
  let running = false;

  async function exportSelected() {
    if (running) return;
    const btn = document.getElementById('yt-export-btn');
    const label = btn.textContent;

    const selected = [...document.querySelectorAll('ytcp-video-row')].filter(isSelected);
    if (!selected.length) {
      alert('Nejsou vybraná žádná videa.\nZaškrtni checkboxy u videí, která chceš exportovat.');
      return;
    }

    running = true;
    const rows = selected.map(parseRow);
    const exportedAt = Date.now();
    const records = [];
    let failed = 0;
    let noRetention = 0;
    let noTraffic = 0;

    for (let i = 0; i < rows.length; i++) {
      btn.textContent = `Stahuji data ${i + 1}/${rows.length}…`;
      const page = await fetchWatchPage(rows[i].id);
      const [ret, traf] = await Promise.all([loadRetention(rows[i].id), loadTraffic(rows[i].id)]);
      const rec = buildRecord(rows[i], page, exportedAt, ret, traf);
      if (rec.popis_kompletni !== 'ano') failed++;
      if (rec.retence_nactena !== 'ano') noRetention++;
      if (rec.zdroje_nactene !== 'ano') noTraffic++;
      records.push(rec);
      await new Promise((r) => setTimeout(r, 300));
    }

    console.table(records);
    const stamp = localParts(new Date(exportedAt)).date;
    download(`youtube-shorts-export-${stamp}.csv`, toCsv(records));

    btn.textContent = label;
    running = false;
    const msgs = [];
    if (failed) {
      msgs.push(`U ${failed} videí se nepodařilo stáhnout data ze stránky videa (popis_kompletni = NE). ` +
        'Chybí u nich délka, čas publikace a tagy a popis je zkrácený.');
    }
    if (noRetention) {
      msgs.push(`U ${noRetention} videí se nenačetla retence (retence_nactena = NE). ` +
        'Buď je video moc čerstvé (Studio počítá data až 2 dny), nebo se stránka analytiky nenačetla.');
    }
    if (noTraffic) {
      msgs.push(`U ${noTraffic} videí se nenačetla tabulka zdrojů návštěvnosti (zdroje_nactene = NE).`);
    }
    if (msgs.length) alert(msgs.join('\n\n'));
  }

  function addButton() {
    if (document.getElementById('yt-export-btn')) return;
    const btn = document.createElement('button');
    btn.id = 'yt-export-btn';
    btn.textContent = '⬇ Export vybraných (CSV)';
    Object.assign(btn.style, {
      position: 'fixed', bottom: '20px', right: '20px', zIndex: 99999,
      padding: '10px 16px', background: '#3ea6ff', color: '#000', border: 'none',
      borderRadius: '6px', fontSize: '14px', fontWeight: '600', cursor: 'pointer',
      boxShadow: '0 2px 8px rgba(0,0,0,.4)',
    });
    btn.addEventListener('click', exportSelected);
    document.body.appendChild(btn);
  }

  // hák pro testy mimo prohlížeč
  if (typeof __YT_TEST__ !== 'undefined') {
    __YT_TEST__.fns = { parseTraffic, summarizeSources, parseRetention, deepText, fmtNumber, parseWatchPage, buildRecord, toCsv, extractHashtags, cleanNumber, listDateToIso };
    return;
  }
  setInterval(addButton, 1500);
})();