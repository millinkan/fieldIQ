import { api } from './api.js'
import {
  renderSimulate, renderRoster, renderPDV, renderSRR,
  renderModel, renderPipeline, renderBlueprint, renderAPI, renderIntelligence,
  pdvColor,
} from './panels.js'

// ── State ──────────────────────────────────────────────────
const state = {
  currentTab: 'simulate',
  players: [],
  playerStatuses: {},   // { player_id: 'ok'|'injured'|'bench' }
  srrScenario: 'striker',
  pdvData: [],
  srrData: [],
  modelArch: null,
  modelRankings: [],
  apiEndpoints: [],
  credits: null,
  intelligenceData: null,
}

const STATUS_CYCLE = ['ok', 'injured', 'bench']

// ── Boot ───────────────────────────────────────────────────
async function boot() {
  checkHealth()

  // Preload all data in parallel
  const [players, pdv, srr, arch, rankings, endpoints, credits] = await Promise.allSettled([
    api.players('BRA'),
    api.pdvScores(),
    api.srrRankings('striker'),
    api.modelArch(),
    api.modelRankings(),
    api.endpoints(),
    api.credits(),
  ])

  if (players.status === 'fulfilled') {
    state.players = players.value.players
    state.players.forEach(p => { state.playerStatuses[p.id] = 'ok' })
  }
  if (pdv.status === 'fulfilled')       state.pdvData = pdv.value.players
  if (srr.status === 'fulfilled')       state.srrData = srr.value.rankings
  if (arch.status === 'fulfilled')      state.modelArch = arch.value
  if (rankings.status === 'fulfilled')  state.modelRankings = rankings.value.rankings
  if (endpoints.status === 'fulfilled') state.apiEndpoints = endpoints.value.endpoints
  if (credits.status === 'fulfilled')   state.credits = credits.value

  renderTab('simulate')
  wireNavTabs()
}

// ── Health check ───────────────────────────────────────────
async function checkHealth() {
  const pill = document.getElementById('api-status')
  try {
    await api.health()
    pill.innerHTML = '<span class="dot"></span> API live'
    pill.classList.remove('err')
  } catch {
    pill.innerHTML = '<span class="dot"></span> API offline'
    pill.classList.add('err')
  }
}

// ── Tab routing ────────────────────────────────────────────
function wireNavTabs() {
  document.getElementById('nav-tabs').addEventListener('click', e => {
    const btn = e.target.closest('.tab')
    if (!btn) return
    const tab = btn.dataset.tab
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'))
    btn.classList.add('active')
    renderTab(tab)
    state.currentTab = tab
  })
}

function renderTab(tab) {
  const main = document.getElementById('main-content')
  main.innerHTML = ''
  const div = document.createElement('div')
  div.className = 'panel active'

  switch (tab) {
    case 'simulate':  div.innerHTML = renderSimulate();                              break
    case 'roster':    div.innerHTML = renderRoster(state.players);                   break
    case 'pdv':       div.innerHTML = renderPDV(state.pdvData);                      break
    case 'srr':       div.innerHTML = renderSRR(normSRR(), state.srrScenario);        break
    case 'intelligence': div.innerHTML = renderIntelligence();                       break
    case 'model':     div.innerHTML = renderModel(state.modelArch, state.modelRankings); break
    case 'pipeline':  div.innerHTML = renderPipeline();                              break
    case 'blueprint': div.innerHTML = renderBlueprint();                             break
    case 'api':       div.innerHTML = renderAPI(state.apiEndpoints, state.credits);  break
  }

  main.appendChild(div)
  wireTabEvents(tab)
}

function normSRR() {
  if (state.srrData.length && typeof state.srrData[0].srr === 'number') {
    return state.srrData.map(r => ({
      flag: r.flag,
      name: r.name,
      srr: { [state.srrScenario]: r.srr },
      delta: { [state.srrScenario]: r.delta },
    }))
  }
  if (state.srrData.length && state.srrData[0].srr?.[state.srrScenario] != null) {
    return state.srrData
  }
  return [
    {flag:"🇫🇷",name:"France",srr:{striker:88,mid:91,def:85,gk:78},delta:{striker:-3,mid:-5,def:-8,gk:-15}},
    {flag:"🇧🇷",name:"Brazil",srr:{striker:71,mid:83,def:80,gk:62},delta:{striker:-18,mid:-9,def:-12,gk:-22}},
    {flag:"🇪🇸",name:"Spain",srr:{striker:84,mid:92,def:87,gk:80},delta:{striker:-7,mid:-4,def:-6,gk:-11}},
    {flag:"🇦🇷",name:"Argentina",srr:{striker:58,mid:76,def:78,gk:71},delta:{striker:-28,mid:-14,def:-10,gk:-13}},
    {flag:"🏴󠁧󠁢󠁥󠁮󠁧󠁿",name:"England",srr:{striker:79,mid:81,def:83,gk:85},delta:{striker:-12,mid:-11,def:-9,gk:-8}},
    {flag:"🇵🇹",name:"Portugal",srr:{striker:45,mid:68,def:72,gk:74},delta:{striker:-35,mid:-20,def:-15,gk:-12}},
  ]
}

// ── Per-tab event wiring ───────────────────────────────────
function wireTabEvents(tab) {
  if (tab === 'simulate') {
    document.getElementById('run-sim-btn')?.addEventListener('click', runSimulation)
  }

  if (tab === 'roster') {
    document.querySelectorAll('.player-slot').forEach(slot => {
      slot.addEventListener('click', () => {
        const idx  = parseInt(slot.dataset.idx)
        const pid  = slot.dataset.id
        const cur  = STATUS_CYCLE.indexOf(state.playerStatuses[pid] || 'ok')
        const next = STATUS_CYCLE[(cur + 1) % STATUS_CYCLE.length]
        state.playerStatuses[pid] = next
        updateSlot(slot, idx, next)
        recalcSynergy()
      })
    })
    document.getElementById('recalc-btn')?.addEventListener('click', () => {
      callSynergyAPI()
    })
    recalcSynergy()
  }

  if (tab === 'srr') {
    document.getElementById('srr-pills')?.addEventListener('click', e => {
      const btn = e.target.closest('.pill')
      if (!btn) return
      state.srrScenario = btn.dataset.sc
      renderTab('srr')
    })
  }

  if (tab === 'intelligence') {
    document.getElementById('run-analysis-btn')?.addEventListener('click', runIntelligence)
  }

  if (tab === 'api') {
    document.addEventListener('click', e => {
      const hdr = e.target.closest('.ep-header')
      if (!hdr) return
      const i = hdr.dataset.ep
      document.getElementById(`epb-${i}`)?.classList.toggle('open')
    })
  }
}

// ── Roster logic ───────────────────────────────────────────
function updateSlot(slot, idx, status) {
  slot.className = `player-slot ${status}`
  const dot = document.getElementById(`dot-${idx}`)
  if (dot) dot.className = `status-dot dot-${status === 'ok' ? 'ok' : status === 'injured' ? 'inj' : 'bench'}`
}

function recalcSynergy() {
  const active  = state.players.filter(p => (state.playerStatuses[p.id] || 'ok') === 'ok')
  const injured = state.players.filter(p => state.playerStatuses[p.id] === 'injured')

  if (!active.length) return

  const avgRtg  = active.reduce((s, p) => s + p.rating, 0) / active.length
  const avgPdv  = active.reduce((s, p) => s + p.pdv, 0) / active.length
  const penalty = injured.reduce((s, p) => s + (p.rating - 70) * 0.03, 0)

  const syn   = Math.max(40, Math.min(99, avgRtg - penalty * 3 - avgPdv * 0.8)).toFixed(1)
  const xg    = Math.max(0.4, 2.41 - penalty * 0.18 - avgPdv * 0.05).toFixed(2)
  const press = Math.max(30, Math.round(68 - injured.length * 5))
  const xga   = Math.min(3.5, 1.12 + penalty * 0.12).toFixed(2)

  setEl('syn-score', syn)
  setEl('xg-proj', xg)
  setEl('press-v', press + '%')
  setEl('xga-v', xga)

  renderSynBars(active, injured)
}

function renderSynBars(active, injured, apiDims = null) {
  const injN = injured.length
  const dimMap = apiDims ? [
    {l:'Attacking synergy',  v: apiDims.attacking_synergy, c:'var(--lime)'},
    {l:'Defensive shape',    v: apiDims.defensive_shape, c:'var(--sky)'},
    {l:'Press cohesion',     v: apiDims.press_cohesion, c:'var(--lime)'},
    {l:'Set piece threat',   v: apiDims.set_piece_threat, c:'var(--amber)'},
    {l:'Tactical flex',      v: apiDims.tactical_flexibility, c:'var(--sky)'},
    {l:'PDV risk-adjusted',  v: apiDims.pdv_adjusted_risk, c:'var(--red)'},
  ] : [
    {l:'Attacking synergy',  base:82, c:'var(--lime)'},
    {l:'Defensive shape',    base:78, c:'var(--sky)'},
    {l:'Press cohesion',     base:71, c:'var(--lime)'},
    {l:'Set piece threat',   base:65, c:'var(--amber)'},
    {l:'Tactical flex',      base:74, c:'var(--sky)'},
    {l:'PDV risk-adjusted',  base:Math.round((1 - active.reduce((s,p)=>s+p.pdv,0)/(active.length||1)/4)*100), c:'var(--red)'},
  ]
  const container = document.getElementById('syn-bars')
  if (!container) return
  container.innerHTML = dimMap.map(d => {
    const v = apiDims
      ? Math.round(d.v)
      : Math.max(10, Math.min(99, d.base - injN * 3.5))
    return `
      <div class="syn-row">
        <span class="syn-lbl">${d.l}</span>
        <div class="syn-trk"><div class="syn-fill" style="width:${v}%;background:${d.c}"></div></div>
        <span class="syn-val" style="color:${d.c}">${v}</span>
      </div>`
  }).join('')
}

async function callSynergyAPI() {
  const statuses = state.players.map(p => ({
    player_id: p.id, status: state.playerStatuses[p.id] || 'ok',
  }))
  try {
    const res = await api.synergy({ team_id: 'BRA', opponent_id: 'FRA', player_statuses: statuses })
    setEl('syn-score', res.synergy_score)
    setEl('xg-proj', res.xg_projected)
    setEl('press-v', res.press_intensity + '%')
    setEl('xga-v', res.xga_exposed)
    if (res.synergy_dimensions) {
      const active = state.players.filter(p => (state.playerStatuses[p.id] || 'ok') === 'ok')
      const injured = state.players.filter(p => state.playerStatuses[p.id] === 'injured')
      renderSynBars(active, injured, res.synergy_dimensions)
    }
  } catch (e) {
    console.warn('Synergy API error, using client calc:', e.message)
  }
}

// ── Tournament simulation ──────────────────────────────────
async function runSimulation() {
  const btn = document.getElementById('run-sim-btn')
  if (!btn) return

  btn.classList.add('btn-loading')
  btn.innerHTML = '<span class="spinner"></span>Simulating 1,000 tournaments...'

  const injuries = {}
  state.players.forEach(p => {
    if (state.playerStatuses[p.id] === 'injured') {
      if (!injuries['BRA']) injuries['BRA'] = []
      injuries['BRA'].push(p.id)
    }
  })

  try {
    const res = await api.simulate({
      n_simulations: 1000,
      elo_weight:  (parseInt(document.getElementById('eloW')?.value)  || 40) / 100,
      form_weight: (parseInt(document.getElementById('formW')?.value) || 25) / 100,
      pdv_weight:  (parseInt(document.getElementById('pdvW')?.value)  || 20) / 100,
      xg_weight:   (parseInt(document.getElementById('xgW')?.value)   || 15) / 100,
      srr_weight:  (parseInt(document.getElementById('srrW')?.value)  || 10) / 100,
      injuries: Object.keys(injuries).length ? injuries : null,
    })
    renderSimResults(res)
  } catch (e) {
    document.getElementById('sim-results').innerHTML = `
      <div class="alert alert-red"><span>⚠</span><div><strong>API Error</strong>${e.message}</div></div>`
  } finally {
    btn.classList.remove('btn-loading')
    btn.innerHTML = '▶ Run Full 48-Team Tournament Simulation'
  }
}

function renderSimResults(res) {
  const out = document.getElementById('sim-results')
  if (!out) return

  const c = res.display_champion
  const injAlert = res.display_champion && Object.keys(state.playerStatuses).some(k => state.playerStatuses[k] === 'injured')
    ? `<div class="alert alert-red" style="animation:fadeUp .3s .1s ease both">
        <span>🟥</span><div><strong>Roster penalty applied</strong>Injured players reduced their team's xG and SRR in this simulation run.</div>
       </div>` : ''

  // Top 5 champion probs
  const top5 = Object.entries(res.champion_probs).slice(0, 5)
    .map(([name, prob], i) => `
      <div class="pb-row">
        <span class="pb-rank">${i+1}</span>
        <span class="pb-name">${name}</span>
        <div class="pb-track"><div class="pb-fill" style="width:${(prob*100*3).toFixed(0)}%"></div></div>
        <span class="pb-pct">${(prob*100).toFixed(1)}%</span>
      </div>`).join('')

  // Groups (first 8)
  const groupBoxes = (res.group_results || []).map(g => `
    <div class="group-box">
      <div class="group-label">Group ${g.group}</div>
      ${g.teams.map(t => `<div class="group-team"><span>${t.flag || ''} ${t.name}</span><span class="group-adv">${t.advance ? '✓' : ''}</span></div>`).join('')}
    </div>`).join('')

  // KO bracket
  const koHTML = Object.entries(res.ko_results || {}).map(([rnd, teams]) => `
    <div class="ko-round-label">${rnd}</div>
    ${teams.map(t => `<div class="ko-team"><span>${t.flag || ''} ${t.name}</span></div>`).join('')}`).join('')

  out.innerHTML = `
    <div class="champ-banner">
      <div style="font-size:1.5rem;margin-bottom:.25rem">🏆</div>
      <div class="champ-label">2026 World Cup Champion</div>
      <div class="champ-name">${c?.flag || ''} ${c?.name || 'Unknown'}</div>
      <div style="font-size:10px;color:var(--muted);margin-top:.2rem">
        ELO ${c?.elo?.toFixed(0) || '—'} · PDV ${c?.pdv?.toFixed(1) || '—'} · ${res.n_simulations.toLocaleString()} simulations
      </div>
    </div>

    ${injAlert}

    <div class="card" style="animation:fadeUp .3s .15s ease both">
      <div class="card-title">Final — ${res.display_finalist_a?.flag || ''} ${res.display_finalist_a?.name || ''} vs ${res.display_finalist_b?.flag || ''} ${res.display_finalist_b?.name || ''}</div>
      <div style="text-align:center;padding:.25rem;font-family:var(--font-ui);font-size:.85rem;font-weight:700;color:var(--lime)">
        🏆 ${c?.name || 'Unknown'} wins
      </div>
    </div>

    <div class="card" style="animation:fadeUp .3s .2s ease both">
      <div class="card-title">Champion Probabilities — Top 5</div>
      ${top5}
    </div>

    <div class="card" style="animation:fadeUp .3s .25s ease both">
      <div class="card-title">Group Stage</div>
      <div class="group-grid">${groupBoxes}</div>
    </div>

    <div class="card" style="animation:fadeUp .3s .3s ease both">
      <div class="card-title">Knockout Bracket</div>
      ${koHTML}
    </div>
  `
}

async function runIntelligence() {
  const btn = document.getElementById('run-analysis-btn')
  const out = document.getElementById('intel-results')
  if (!btn || !out) return
  btn.classList.add('btn-loading')
  try {
    const res = await api.fullAnalysis({
      team_a: { id: 'BRA', name: 'Brazil', elo: 2091, xg: 2.3, pdv: 1.2 },
      team_b: { id: 'FRA', name: 'France', elo: 2005, xg: 2.1, pdv: 1.8 },
      match_number: 3,
      players_a: state.players,
      players_b: [],
    })
    state.intelligenceData = res
    out.innerHTML = `
      <div class="card"><div class="card-title">Pre-Match Edge Score</div>
        <div style="font-family:var(--font-mono);font-size:1.4rem;color:var(--lime)">${res.edge_score} · ${res.edge_label}</div>
      </div>
      <div class="card"><div class="card-title">Layer Breakdown</div>
        <pre style="font-size:10px;color:var(--muted);overflow:auto">${JSON.stringify(res.layers, null, 2)}</pre>
      </div>`
  } catch (e) {
    out.innerHTML = `<div class="alert alert-red">${e.message}</div>`
  } finally {
    btn.classList.remove('btn-loading')
  }
}

// ── Utils ──────────────────────────────────────────────────
function setEl(id, val) {
  const el = document.getElementById(id)
  if (el) el.textContent = val
}

// ── Start ──────────────────────────────────────────────────
boot()
