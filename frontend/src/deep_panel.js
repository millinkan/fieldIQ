/**
 * Deep Intelligence Panel — v4
 * Three new layers beyond probability numbers:
 *   Pathways & Ranges Array
 *   Sensitivity Index (What-If shock matrix)
 *   Structural Asymmetry Rating
 */

import { api } from './api.js'

const FIXTURES = [
  { id: 'BRA-FRA', home_id: 'BRA', away_id: 'FRA', label: '🇧🇷 Brazil vs 🇫🇷 France',      round: 'Quarter-finals', match_number: 5 },
  { id: 'ENG-ESP', home_id: 'ENG', away_id: 'ESP', label: '🏴󠁧󠁢󠁥󠁮󠁧󠁿 England vs 🇪🇸 Spain',     round: 'Quarter-finals', match_number: 5 },
  { id: 'ARG-GER', home_id: 'ARG', away_id: 'GER', label: '🇦🇷 Argentina vs 🇩🇪 Germany', round: 'Round of 16',    match_number: 4 },
  { id: 'FRA-ESP', home_id: 'FRA', away_id: 'ESP', label: '🇫🇷 France vs 🇪🇸 Spain',      round: 'Semi-finals',   match_number: 6 },
]

export function renderDeepIntelligence() {
  return `
<div id="di-root">
  <div class="kicker">v4 · Pathways · Sensitivity Index · Structural Asymmetry Rating</div>
  <div class="panel-title">Deep Intelligence Engine</div>
  <div class="di-info-box">
    A flat 60% win probability is a lazy abstraction. This engine maps how that probability
    is constructed, what breaks it under event shocks, and where the market's pricing model
    is structurally wrong — not by how much, but <em>why</em>.
  </div>

  <div class="di-controls">
    <select id="di-fixture" onchange="diLoad()">
      ${FIXTURES.map(f => `<option value="${f.id}">${f.label} — ${f.round}</option>`).join('')}
    </select>
    <button class="btn btn-lime" id="di-run-btn" onclick="diLoad()" style="margin-bottom:0;width:auto;padding:.55rem 1.25rem">
      Run Deep Analysis
    </button>
  </div>

  <div id="di-body">
    <div class="di-empty">
      <i class="ti ti-brain" style="font-size:28px;color:var(--muted)" aria-hidden="true"></i>
      <div style="color:var(--muted);font-size:13px;margin-top:8px">
        Select a fixture and run the deep analysis
      </div>
    </div>
  </div>
</div>`
}

export async function bootDeepIntelligence() {
  // Auto-load first fixture
  await loadDeepAnalysis(FIXTURES[0])
}

window.diLoad = async function() {
  const sel = document.getElementById('di-fixture')
  const id  = sel?.value || FIXTURES[0].id
  const fix = FIXTURES.find(f => f.id === id) || FIXTURES[0]
  await loadDeepAnalysis(fix)
}

async function loadDeepAnalysis(fixture) {
  const body = document.getElementById('di-body')
  const btn  = document.getElementById('di-run-btn')
  if (!body) return

  body.innerHTML = `<div class="cc-loading"><i class="ti ti-loader-2" style="animation:spin 1s linear infinite;font-size:18px" aria-hidden="true"></i> Running ${fixture.label || fixture.id} deep analysis…</div>`
  if (btn) { btn.disabled = true; btn.textContent = 'Running…' }

  let data
  try {
    data = await fetchDeepFull(fixture)
  } catch (e) {
    data = mockDeepData(fixture)
  }

  renderDeepBody(body, data, fixture)
  if (btn) { btn.disabled = false; btn.textContent = 'Run Deep Analysis' }
}

async function fetchDeepFull(fixture) {
  return api.deepFull({
    home_id:      fixture.home_id,
    away_id:      fixture.away_id,
    ko_round:     fixture.round,
    match_number: fixture.match_number,
    n_sims:       10000,
  })
}

function renderDeepBody(body, data, fixture) {
  const clusters   = data.pathways?.clusters || []
  const shocks     = data.sensitivity?.shocks || []
  const asym       = data.asymmetry || {}
  const summary    = data.executive_summary || {}
  const baseline   = data.baseline_probability || {}

  body.innerHTML = `

<!-- Executive Summary -->
<div class="di-summary-bar">
  <div class="di-summary-severity di-sev-${(asym.severity_label||'NEUTRAL').toLowerCase()}">
    ${asym.severity_label || 'NEUTRAL'}
  </div>
  <div class="di-summary-text">${summary.one_line || '—'}</div>
</div>

<!-- Three column layout -->
<div class="di-grid">

  <!-- ── Layer A: Pathways & Ranges ─────────────────────────────── -->
  <div class="di-section">
    <div class="di-section-header">
      <span class="di-section-num">A</span>
      <div>
        <div class="di-section-title">Pathways &amp; Ranges Array</div>
        <div class="di-section-sub">How the ${pct(baseline.p_win || 0)} is constructed across ${(data.pathways?.total_runs || 10000).toLocaleString()} runs</div>
      </div>
    </div>

    <div class="di-baseline-row">
      <span class="di-bl-label">Baseline</span>
      <span class="di-bl-win">${pct(baseline.p_win||0)} W</span>
      <span class="di-bl-draw">${pct(baseline.p_draw||0)} D</span>
      <span class="di-bl-loss">${pct(baseline.p_loss||0)} L</span>
    </div>

    ${clusters.map((c, i) => clusterCard(c, i)).join('')}

    <div class="di-cluster-note">
      Dominant pathway: <strong>${clusters[0]?.label || '—'}</strong>.
      Each cluster is a distinct tactical archetype within the simulation —
      operators price them individually, not as a single probability.
    </div>
  </div>

  <!-- ── Layer B: Sensitivity Index ─────────────────────────────── -->
  <div class="di-section">
    <div class="di-section-header">
      <span class="di-section-num">B</span>
      <div>
        <div class="di-section-title">Sensitivity Index</div>
        <div class="di-section-sub">What-If shock matrix — where in-play lines will be wrong</div>
      </div>
    </div>

    ${shocks.slice(0, 6).map(s => shockRow(s)).join('')}

    <div class="di-shock-note">
      Asymmetry = market expected move − engine expected move.
      Positive = market over-reacts. Negative = market under-reacts.
      These are the live pricing errors sharp syndicates will exploit.
    </div>
  </div>

  <!-- ── Layer C: Structural Asymmetry ──────────────────────────── -->
  <div class="di-section di-full-width">
    <div class="di-section-header">
      <span class="di-section-num">C</span>
      <div>
        <div class="di-section-title">Structural Asymmetry Rating</div>
        <div class="di-section-sub">The mechanism of mispricing — not the size, the why</div>
      </div>
    </div>

    <div class="di-asym-header">
      <div class="di-asym-score-wrap">
        <div class="di-asym-score ${asymScore(asym.overall_asymmetry_rating||0)}">${fmtScore(asym.overall_asymmetry_rating||0)}</div>
        <div class="di-asym-score-label">Overall rating</div>
      </div>
      <div class="di-asym-narr-wrap">
        <div class="di-narr-block">
          <div class="di-narr-label">Market narrative</div>
          <div class="di-narr-text">${asym.market_narrative || '—'}</div>
        </div>
        <div class="di-narr-block" style="margin-top:.5rem">
          <div class="di-narr-label engine">Engine reality</div>
          <div class="di-narr-text">${asym.engine_narrative || '—'}</div>
        </div>
      </div>
    </div>

    ${(asym.asymmetries || []).map(a => asymmetryCard(a)).join('')}

    <div class="di-commercial">
      <div class="di-commercial-label">Commercial implication</div>
      <div class="di-commercial-text">${asym.commercial_implication || '—'}</div>
    </div>

    <div class="di-action-row">
      <div class="di-action-cell">
        <div class="di-action-label">For trading desk</div>
        <div class="di-action-text">${summary.for_trading_desk || '—'}</div>
      </div>
      <div class="di-action-cell">
        <div class="di-action-label">For syndicate</div>
        <div class="di-action-text">${summary.for_syndicate || '—'}</div>
      </div>
    </div>
  </div>

</div>`
}

// ── Card renderers ─────────────────────────────────────────────────────────

function clusterCard(c, i) {
  const pctWidth = Math.round(c.probability * 100 * 3)
  const colors   = ['var(--lime)', 'var(--sky)', 'var(--red)', 'var(--muted)', 'var(--amber)']
  const color    = colors[i] || 'var(--muted)'
  const isTop    = i === 0
  return `
<div class="di-cluster${isTop ? ' di-cluster-top' : ''}">
  <div class="di-cluster-head">
    <div class="di-cluster-label" style="color:${color}">${c.label}</div>
    <div class="di-cluster-pct" style="color:${color}">${c.pct_of_runs}%</div>
  </div>
  <div class="di-cluster-bar-wrap">
    <div class="di-cluster-bar" style="width:${Math.min(100,pctWidth)}%;background:${color}"></div>
  </div>
  <div class="di-cluster-body">
    <div class="di-cluster-desc">${c.description}</div>
    <div class="di-cluster-scores">
      <span class="di-score-pill">avg ${c.avg_score}</span>
      <span class="di-score-pill">modal ${c.modal_score}</span>
      <span class="di-score-pill">win rate ${pct(c.win_rate)}</span>
    </div>
    <div class="di-cluster-driver">${c.driver}</div>
    ${isTop ? `<div class="di-cluster-gap">${c.market_gap}</div>` : ''}
  </div>
</div>`
}

function shockRow(s) {
  const asym = s.asymmetry || 0
  const cls  = asym > 0.02 ? 'over' : asym < -0.02 ? 'under' : 'aligned'
  const clsLabel = { over: 'Over-reacts', under: 'Under-reacts', aligned: 'Aligned' }
  const delta = s.win_equity_delta || 0
  return `
<div class="di-shock">
  <div class="di-shock-head">
    <div class="di-shock-label">${s.label}</div>
    <div class="di-shock-asym di-asym-${cls}">${clsLabel[cls]}</div>
  </div>
  <div class="di-shock-bars">
    <div class="di-shock-bar-row">
      <span class="di-shock-src">Market</span>
      <div class="di-shock-track">
        <div class="di-shock-fill market" style="width:${Math.min(100,Math.abs(s.market_move||0)*300)}%;margin-left:${(s.market_move||0)>0?'50%':'calc(50% - '+Math.min(50,Math.abs(s.market_move||0)*300)+'%)'}"></div>
        <div class="di-shock-midline"></div>
      </div>
      <span class="di-shock-val">${fmtDelta(s.market_move||0)}</span>
    </div>
    <div class="di-shock-bar-row">
      <span class="di-shock-src">Engine</span>
      <div class="di-shock-track">
        <div class="di-shock-fill engine" style="width:${Math.min(100,Math.abs(delta)*300)}%;margin-left:${delta>0?'50%':'calc(50% - '+Math.min(50,Math.abs(delta)*300)+'%)'}"></div>
        <div class="di-shock-midline"></div>
      </div>
      <span class="di-shock-val">${fmtDelta(delta)}</span>
    </div>
  </div>
  <div class="di-shock-narr">${s.narrative}</div>
</div>`
}

function asymmetryCard(a) {
  const typeColors = { TACTICAL: 'var(--sky)', PHYSICAL: 'var(--amber)', PSYCHOLOGICAL: 'var(--lime)' }
  const color = typeColors[a.type] || 'var(--muted)'
  return `
<div class="di-asym-card">
  <div class="di-asym-card-head">
    <span class="di-asym-type" style="color:${color};border-color:${color}40">${a.type}</span>
    <span class="di-asym-id">${a.id.replace(/_/g,' ')}</span>
    <span class="di-asym-sev di-sev-${(a.severity||'MILD').toLowerCase()}">${a.severity}</span>
    <span class="di-asym-score-sm ${a.score >= 0 ? 'pos' : 'neg'}">${fmtScore(a.score)}</span>
  </div>
  <div class="di-asym-two-col">
    <div>
      <div class="di-narr-label">Market assumes</div>
      <div class="di-narr-text">${a.market_assumption}</div>
    </div>
    <div>
      <div class="di-narr-label engine">Engine finds</div>
      <div class="di-narr-text">${a.engine_reality}</div>
    </div>
  </div>
  <div class="di-asym-narrative">${a.narrative}</div>
</div>`
}

// ── Helpers ───────────────────────────────────────────────────────────────
function pct(v)      { return (v * 100).toFixed(1) + '%' }
function fmtDelta(v) { return (v >= 0 ? '+' : '') + (v * 100).toFixed(1) + 'pp' }
function fmtScore(v) { return (v >= 0 ? '+' : '') + v.toFixed(3) }
function asymScore(v){ return v > 0.04 ? 'pos' : v < -0.04 ? 'neg' : 'neu' }

// ── Mock data fallback ────────────────────────────────────────────────────
function mockDeepData(fixture) {
  return {
    version: '4.0',
    match: { home: fixture.home_id, away: fixture.away_id },
    baseline_probability: { p_win: 0.362, p_draw: 0.221, p_loss: 0.417 },
    executive_summary: {
      one_line: 'MODERATE structural asymmetry. Dominant pathway: Attrition cluster (34% of runs, modal score 1-0). Biggest in-play mispricing: Red card home before 60\' (asymmetry +4.1pp vs market).',
      for_trading_desk: 'Reprice total goals downward — tactical chokehold compresses scoring below public expectation.',
      for_syndicate: 'Edge window: before red card line correction. Primary anomaly: press exhaustion trap.',
    },
    pathways: {
      total_runs: 10000,
      dominant_pathway: 'attrition',
      clusters: [
        { id:'attrition', label:'Attrition cluster', description:'0-0 until 70th min. Superior bench depth breaks deadlock late.', probability:0.34, pct_of_runs:34.0, avg_score:'1.1–0.7', modal_score:'1–0', win_rate:0.68, driver:'SRR bench 71 · late-surge 1.18x', market_gap:'Nil-nil at 70 min priced as draw. SRR bench quality means the deadlock resolves as a win 68% of the time. Market treats it as a draw.' },
        { id:'dominance', label:'Dominance cluster', description:'Early goal within 20 mins, opponent defensive block collapses.', probability:0.28, pct_of_runs:28.0, avg_score:'2.9–0.6', modal_score:'3–0', win_rate:0.91, driver:'Early GRD +0.31 · press efficacy 0.52', market_gap:'ELO model prices a competitive game. Tactical engine says this collapses into a 3-0 pattern 28% of the time — not priced.' },
        { id:'tactical_stalemate', label:'Tactical stalemate', description:'Style neutralisation — POSSESSION vs COUNTER locks into controlled territory.', probability:0.21, pct_of_runs:21.0, avg_score:'0.8–0.5', modal_score:'0–0', win_rate:0.41, driver:'Style matrix POSSESSION vs COUNTER', market_gap:'Public expects open attacking play. Engine: controlled chokehold. In-play over/under 2.5 is overpriced.' },
        { id:'counter_exposure', label:'Counter exposure', description:'High defensive line caught on transition — structural upset pathway.', probability:0.10, pct_of_runs:10.0, avg_score:'0.7–1.4', modal_score:'0–1', win_rate:0.12, driver:'High-line 0.62 vs pace 0.80', market_gap:'Market prices this as 5% upset probability. Engine says 10% — the high-line counter is a structural inevitability, not a fluke.' },
        { id:'chaos', label:'Chaos cluster', description:'High-scoring, both teams exposed in transition post-70.', probability:0.07, pct_of_runs:7.0, avg_score:'2.8–2.1', modal_score:'3–2', win_rate:0.55, driver:'Combined PDV 3.0 · press exhaustion active', market_gap:'BTTS in this cluster is 89% — structurally underweighted in public pre-match pricing.' },
      ],
    },
    sensitivity: {
      baseline_win_prob: 0.362,
      shocks: [
        { event:'red_card_home_pre60', label:'Red card — before 60\'', win_equity_delta:-0.178, market_move:-0.224, asymmetry:0.046, asymmetry_direction:'market_over_reacts', narrative:'Bench depth (SRR 71) and defensive shape absorb a red card better than market assumes. Market drops 22.4% — engine: 17.8%. Gap of 4.6pp is exploitable.' },
        { event:'concede_first', label:'Goes 1-0 down', win_equity_delta:-0.158, market_move:-0.185, asymmetry:0.027, asymmetry_direction:'market_over_reacts', narrative:'Goal_Response_Delta +0.31. Team surges after conceding. Market drops 18.5% — engine 15.8%. Historical comeback rate 38%.' },
        { event:'high_line_counter', label:'High-line counter materialises', win_equity_delta:-0.098, market_move:-0.06, asymmetry:-0.038, asymmetry_direction:'market_under_reacts', narrative:'HIGH-RISK FLAG ACTIVE. Defensive line 0.62 vs pace 0.80. Market drops only 6% — engine says 9.8%. Market significantly underprices this event.' },
        { event:'score_first', label:'Goes 1-0 up', win_equity_delta:0.228, market_move:0.210, asymmetry:-0.018, asymmetry_direction:'aligned', narrative:'Late-surge 1.18x amplifies the lead. Engine: +22.8% vs market +21.0%. Near-aligned.' },
        { event:'press_breakthrough', label:'High press lands', win_equity_delta:0.062, market_move:0.080, asymmetry:0.018, asymmetry_direction:'aligned', narrative:'Press efficacy 0.52. Engine slightly below market on this event — no exhaustion flag.' },
        { event:'injury_sub_key_player', label:'Injury substitution', win_equity_delta:-0.058, market_move:-0.065, asymmetry:0.007, asymmetry_direction:'aligned', narrative:'SRR 71 — bench cover adequate. Market at −6.5%, engine at −5.8%. Near-aligned.' },
      ],
      biggest_asymmetry: 'red_card_home_pre60',
    },
    asymmetry: {
      overall_asymmetry_rating: 0.061,
      severity_label: 'MODERATE',
      direction: 'structural_advantage_home',
      market_narrative: 'Market prices this as a balanced, potentially high-scoring QF between two strong attacking sides. ELO-based models favour the home team narrowly.',
      engine_narrative: 'MODERATE structural asymmetry detected (TACTICAL, PHYSICAL). Primary anomaly: Press Exhaustion Trap. The market does not model late-game xG decay from press exhaustion against a press-resistant opponent.',
      commercial_implication: 'Sportsbook: reprice total goals downward — press exhaustion will compress scoring in the final 15 minutes. In-play over/under 2.5 (75\'–90\') is overpriced. Set live lines to move against the pressing team as fatigue compounds. MODERATE — monitoring window is days, not hours.',
      asymmetries: [
        { type:'TACTICAL', id:'press_exhaustion_trap', score:-0.048, severity:'MODERATE', direction:'favours_away', market_assumption:'Market rewards pressing teams in win probability. Standard models don\'t model energy depletion.', engine_reality:'PPDA 8.8 (aggressive press) vs pass completion under pressure 0.74. Engine projects late-game xG penalty −0.14 in mins 75–90. Market will over-price the pressing team in late in-play window.', narrative:'Press exhaustion trap active. Late-game drop −14% win equity. In-play over/under 0.5 goals (75\'–90\') systematically mispriced.' },
        { type:'PHYSICAL', id:'travel_fatigue_gap', score:0.038, severity:'MILD', direction:'favours_home', market_assumption:'Market uses general squad quality and form. No travel itinerary data in standard models.', engine_reality:'Home team cumulative fatigue 0.089. Away team 0.142. Sprint speed differential: 0.94 vs 0.88. Timezone shift 4h for away side.', narrative:'Physical asymmetry: away team is measurably more fatigued. Market prices squad strength — FieldIQ prices sprint speed.' },
      ],
    },
  }
}
