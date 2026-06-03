/* ── Simulate Panel ── */
export function renderSimulate() {
  return `
    <div class="kicker">48-Team · Monte Carlo · PyTorch MLP · PDV + SRR weighted</div>
    <div class="panel-title">Tournament Simulator — WC 2026</div>

    <div class="card card-l">
      <div class="card-title">MLP Weight Configuration</div>
      ${slider('eloW',   'ELO weight',          40)}
      ${slider('formW',  'Form (last 10)',        25)}
      ${slider('pdvW',   'PDV discipline',        20)}
      ${slider('xgW',    'xG differential',       15)}
      ${slider('srrW',   'SRR bench depth',       10)}
    </div>

    <div class="alert alert-lime">
      <span>💡</span>
      <div><strong>Roster integration</strong>
        Mark injuries in the Roster tab first — those penalties carry into this simulation automatically.</div>
    </div>

    <button class="btn btn-lime" id="run-sim-btn">▶ Run Full 48-Team Tournament Simulation</button>
    <div id="sim-results"></div>
  `
}

/* ── Roster Panel ── */
export function renderRoster(players) {
  const slots = players.map((p, i) => `
    <div class="player-slot ok" id="slot-${i}" data-idx="${i}" data-id="${p.id}">
      <div class="status-dot dot-ok" id="dot-${i}"></div>
      <div class="ps-name">${p.name}</div>
      <div class="ps-pos">${p.pos}</div>
      <div class="ps-stats">
        <span class="ps-stat"><span class="lbl">RTG </span><span style="color:var(--lime)">${p.rating}</span></span>
        <span class="ps-stat"><span class="lbl">PDV </span><span style="color:${pdvColor(p.pdv)}">${p.pdv}</span></span>
      </div>
    </div>`).join('')

  return `
    <div class="kicker">Pillar 1 · Roster-Adjusted Predictive Intelligence</div>
    <div class="panel-title">Live Lineup Builder — Brazil</div>

    <div class="metrics">
      <div class="met"><div class="met-val g" id="syn-score">87.3</div><div class="met-lbl">Synergy</div></div>
      <div class="met"><div class="met-val s" id="xg-proj">2.41</div><div class="met-lbl">xG Proj</div></div>
      <div class="met"><div class="met-val a" id="press-v">68%</div><div class="met-lbl">Press</div></div>
      <div class="met"><div class="met-val r" id="xga-v">1.12</div><div class="met-lbl">xGA Risk</div></div>
    </div>

    <div class="card card-l">
      <div class="card-title">Starting XI <small style="font-weight:400;color:var(--muted);font-size:11px">— click to cycle: OK → Injured → Bench</small></div>
      <div class="roster-grid">${slots}</div>
      <button class="btn btn-lime" style="margin-bottom:0" id="recalc-btn">↻ Recalculate Synergy Vector</button>
    </div>

    <div class="card">
      <div class="card-title">Synergy Breakdown</div>
      <div id="syn-bars"></div>
    </div>

    <div class="alert alert-lime">
      <span>⚡</span>
      <div><strong>Feeds into Simulate</strong>
        Injuries here reduce Brazil's xG and SRR in the tournament bracket.</div>
    </div>
  `
}

/* ── PDV Panel ── */
export function renderPDV(data) {
  const rows = data.map(r => `
    <tr>
      <td style="font-family:var(--font-ui);font-weight:700">${r.player}</td>
      <td style="color:var(--muted)">${r.team}</td>
      <td>
        <div class="mono" style="color:${pdvColor(r.pdv)}">${r.pdv}</div>
        <div class="pdv-mini-bar"><div class="pdv-mini-fill" style="width:${(r.pdv/3*100).toFixed(0)}%;background:${pdvColor(r.pdv)}"></div></div>
      </td>
      <td style="font-family:var(--font-mono)">${r.susp_pct}%</td>
      <td><span class="risk-badge risk-${r.risk}">${r.risk}</span></td>
    </tr>`).join('')

  return `
    <div class="kicker">Pillar 2 · Disciplinary Risk Engine</div>
    <div class="panel-title">Player Discipline Volatility</div>

    <div class="metrics">
      <div class="met"><div class="met-val r">4</div><div class="met-lbl">High-Risk</div></div>
      <div class="met"><div class="met-val a">31%</div><div class="met-lbl">Susp. Prob</div></div>
      <div class="met"><div class="met-val g">−14%</div><div class="met-lbl">Post-Susp Δ</div></div>
      <div class="met"><div class="met-val s">0.83</div><div class="met-lbl">Avg PDV</div></div>
    </div>

    <div class="alert alert-red">
      <span>🟥</span>
      <div><strong>Cascade Alert — Match 2</strong>
        Casemiro (PDV 2.4) picked up a yellow in Match 1. Suspension probability: 38%.
        If suspended, Brazil's defensive midfield cover drops 19%. Sportsbooks: adjust Match 3 futures.</div>
    </div>

    <div class="card card-r">
      <div class="card-title">PDV Table — WC 2026 Cohort</div>
      <table class="data-table">
        <thead><tr><th>Player</th><th>Team</th><th>PDV</th><th>Susp%</th><th>Risk</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>

    <div class="card">
      <div class="card-title">Cascade Simulation — Casemiro suspended R16</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.45rem">
        ${triStat('Base xG',      '2.41', 'g')}
        ${triStat('Post-Susp xG', '1.96', 'a')}
        ${triStat('Win Prob Δ',   '−14%', 'r')}
      </div>
    </div>

    <div class="card card-l" style="font-family:var(--font-mono);font-size:10px;line-height:1.8;color:rgba(184,242,65,.75)">
      <div class="kicker">PDV Formula — feature[11] in the 23-dim MLP input vector</div>
      PDV = (yellows_per_90 × 0.5)<br>
      &nbsp;&nbsp;&nbsp;&nbsp;+ (red_cards_season × 2.5)<br>
      &nbsp;&nbsp;&nbsp;&nbsp;+ (late_game_foul_rate × 1.8)<br>
      &nbsp;&nbsp;&nbsp;&nbsp;− (suspension_cover_score × 0.9)<br>
      <span style="color:var(--muted)">// Higher PDV = more KO-round suspension risk</span>
    </div>
  `
}

/* ── SRR Panel ── */
export function renderSRR(data, scenario) {
  const sorted = [...data].sort((a, b) => b.srr[scenario] - a.srr[scenario])
  const rows = sorted.map(t => {
    const s = t.srr[scenario], d = t.delta[scenario]
    const c = s > 85 ? 'var(--lime)' : s > 70 ? 'var(--amber)' : 'var(--red)'
    return `
      <div class="srr-row">
        <span style="font-size:1.1rem">${t.flag}</span>
        <span style="font-family:var(--font-ui);font-size:12px;font-weight:700;min-width:90px">${t.name}</span>
        <div style="flex:1">
          <div style="height:5px;background:var(--faint);border-radius:3px;overflow:hidden">
            <div style="width:${s}%;height:100%;background:${c};border-radius:3px"></div>
          </div>
        </div>
        <div style="text-align:right;min-width:52px">
          <div style="font-family:var(--font-mono);font-size:12px;color:${c}">${s}</div>
          <div style="font-family:var(--font-mono);font-size:9px;color:${d<-20?'var(--red)':d<-10?'var(--amber)':'var(--lime)'}">${d}%</div>
        </div>
      </div>`
  }).join('')

  const LABELS = {striker:'Striker Lost',mid:'Playmaker Lost',def:'Centre-Back Lost',gk:'Goalkeeper Lost'}

  return `
    <div class="kicker">Pillar 3 · Bench Depth Intelligence</div>
    <div class="panel-title">Squad Robustness Rating™</div>

    <div class="pill-group" id="srr-pills">
      ${['striker','mid','def','gk'].map(sc =>
        `<button class="pill${sc===scenario?' active':''}" data-sc="${sc}">${LABELS[sc]}</button>`
      ).join('')}
    </div>

    <div class="card card-s">
      <div class="card-title">SRR Rankings · Scenario: <span style="color:var(--lime)">${LABELS[scenario]}</span></div>
      <div id="srr-list">${rows}</div>
    </div>

    <div class="alert alert-amber">
      <span>📊</span>
      <div><strong>FootyStats blind spot</strong>
        FootyStats rates squad strength on club name value. SRR measures the actual skill-vector gap
        between starter and backup — a number that compounds as injuries stack mid-tournament.</div>
    </div>
  `
}

/* ── V3 Intelligence Panel ── */
export function renderIntelligence() {
  return `
    <div class="kicker">V3 · Contextual Intelligence</div>
    <div class="panel-title">Pre-Match Full Analysis</div>
    <p style="font-size:12px;color:var(--muted);margin-bottom:1rem">
      Four layers beyond static averages: fatigue & travel, club chemistry, momentum & clutch, tactical matchups.
    </p>
    <button class="btn btn-primary" id="run-analysis-btn">Run BRA vs FRA Analysis</button>
    <div id="intel-results" style="margin-top:1rem"></div>
  `
}

/* ── Model Panel ── */
export function renderModel(arch, rankings) {
  const nFeat = arch?.input_features ?? 35
  const rankRows = (rankings || []).map((r, i) => `
    <div class="pb-row">
      <span class="pb-rank">${i+1}</span>
      <span class="pb-flag">${r.flag}</span>
      <span class="pb-name">${r.name}</span>
      <div class="pb-track"><div class="pb-fill" style="width:${r.champion_pct * 3}%"></div></div>
      <span class="pb-pct">${r.champion_pct}%</span>
    </div>`).join('')

  return `
    <div class="kicker">PyTorch MLP v3 · ${nFeat} features → Softmax 3 · StatsBomb + live data</div>
    <div class="panel-title">Deep Learning Architecture</div>

    <div class="metrics">
      <div class="met"><div class="met-val g">48</div><div class="met-lbl">Teams</div></div>
      <div class="met"><div class="met-val s">4</div><div class="met-lbl">Intel Layers</div></div>
      <div class="met"><div class="met-val a">${nFeat}</div><div class="met-lbl">Features</div></div>
      <div class="met"><div class="met-val r">10k</div><div class="met-lbl">MC Runs</div></div>
    </div>

    <div class="card card-l">
      <div class="card-title">MLP Layer Stack (V3)</div>
      <div class="arch-row">
        <span class="anode an-gold">Input ${nFeat}</span><span class="an-arrow">→</span>
        <span class="anode an-teal">Dense 512</span><span class="an-arrow">→</span>
        <span class="anode an-teal">Dense 256</span><span class="an-arrow">→</span>
        <span class="anode an-teal">Dense 128</span><span class="an-arrow">→</span>
        <span class="anode an-teal">Dense 64</span><span class="an-arrow">→</span>
        <span class="anode an-green">Softmax 3</span>
      </div>
      <div style="font-size:11px;color:var(--muted)">BatchNorm + ReLU + Dropout · CrossEntropyLoss · Adam · ReduceLROnPlateau</div>
    </div>

    <div class="card">
      <div class="card-title">${nFeat}-Feature Input Vector</div>
      <div style="margin-bottom:.5rem">
        <div style="font-size:10px;color:var(--sky);margin-bottom:.25rem">Structural v2 (23)</div>
        ${(arch?.feature_groups?.structural_v2 || []).slice(0,8).map(f=>`<span class="ftag ftag-fifa">${f}</span>`).join('')}
        <span class="ftag ftag-fifa">+15 more</span>
      </div>
      <div style="margin-bottom:.5rem">
        <div style="font-size:10px;color:var(--lime);margin-bottom:.25rem">V3 Intelligence (12)</div>
        ${['Fatigue','Rest decay','TZ shift','Synergy','xT compat','Clutch','Goal response','Penalties','Tactical','Press','High line','Late drop'].map(f=>`<span class="ftag ftag-fs">${f}</span>`).join('')}
      </div>
    </div>

    <div class="card card-l">
      <div class="card-title">Champion Probability Rankings</div>
      ${rankRows}
    </div>
  `
}

/* ── Pipeline Panel ── */
export function renderPipeline() {
  const steps = [
    ['FIFA API Ingest', 'Pull ELO ratings, world rankings, squad metadata and seedings from FIFA official endpoints. Normalize confederation codes, resolve team ID collisions. Cache raw responses to Parquet.'],
    ['FootyStats Scrape', 'Async fetch of match-level xG, PPDA, deep completions, shot maps across 3 qualifying cycles. Exponential backoff (2ˢ delay). Rate-limit aware. Deduplication on (team_id, match_date).'],
    ['PDV Feature Engineering', 'Compute per-player PDV: (yellows/90 × 0.5) + (reds × 2.5) + (late_foul × 1.8) − (cover × 0.9). Aggregate to team-level PDV_diff. This becomes feature[11] in the 23-dim MLP input vector.'],
    ['SRR Bench Scoring', 'Per team, compute the skill-vector gap between starter and backup for each position. SRR = weighted average across 11 slots. Becomes feature[22]. Updates live when injuries are marked in the Roster tab.'],
    ['Schema Alignment', 'Resolve FIFA team_id ↔ FootyStats team_id via RapidFuzz ≥88 fuzzy threshold + 12-entry manual override map for edge cases (USA/United States, Korea/South Korea etc). Join on tournament_year + team_id.'],
    ['Feature Matrix + Training', '23-dim differential vector = team_A_features − team_B_features. StandardScaler fit on train split only (no leakage). MLP trained on WC 1998–2018 + qualifying matches. 80/10/10 split. Best val_loss checkpoint saved.'],
    ['Monte Carlo 10,000-Run Sim', 'Each match samples from MLP softmax [P_win, P_draw, P_loss]. Roster injuries penalise xG/SRR before R1. PDV cascade compounds suspension risk per KO round. Aggregate champion frequencies across all runs.'],
  ]

  return `
    <div class="kicker">7-Step Data Engineering Flow</div>
    <div class="panel-title">FIFA + FootyStats → PyTorch Pipeline</div>
    <div class="card">
      ${steps.map(([title, desc], i) => `
        <div class="pipe-step">
          <div class="pipe-num">${i+1}</div>
          <div><div class="pipe-title">${title}</div><div class="pipe-desc">${desc}</div></div>
        </div>`).join('')}
    </div>
  `
}

/* ── Blueprint Panel ── */
export function renderBlueprint() {
  return `
    <div class="kicker">Complete Python Blueprint</div>
    <div class="panel-title">PyTorch + Pandas + RapidFuzz</div>

    <div class="code-section-label">1 · Data Ingestion — FIFA + FootyStats + PDV + SRR</div>
    <div class="codeblock"><span class="kw">import</span> pandas <span class="kw">as</span> pd, numpy <span class="kw">as</span> np, requests, time
<span class="kw">from</span> rapidfuzz <span class="kw">import</span> process <span class="kw">as</span> rfuzz

<span class="kw">def</span> <span class="fn">fetch_fifa_data</span>() -> pd.DataFrame:
    url = <span class="st">"https://api.fifa.com/api/v3/rankings/FIFA?locale=en"</span>
    raw = requests.get(url, timeout=15).json()[<span class="st">"Results"</span>]
    <span class="kw">return</span> pd.DataFrame([{<span class="st">"team_id"</span>: t[<span class="st">"IdTeam"</span>], <span class="st">"name"</span>: t[<span class="st">"TeamName"</span>][0][<span class="st">"Description"</span>],
        <span class="st">"elo"</span>: t[<span class="st">"Points"</span>], <span class="st">"rank"</span>: t[<span class="st">"Rank"</span>],
        <span class="st">"confederation"</span>: t[<span class="st">"IdConfederation"</span>], <span class="st">"wc_titles"</span>: t.get(<span class="st">"Titles"</span>, 0)
    } <span class="kw">for</span> t <span class="kw">in</span> raw])

<span class="kw">def</span> <span class="fn">compute_pdv</span>(s: dict) -> float:
    <span class="cm"># PDV = feature[11] in 23-dim MLP input vector</span>
    <span class="kw">return</span> (s.get(<span class="st">"yellow_cards_per_90"</span>, 0) * 0.5
          + s.get(<span class="st">"red_cards_season"</span>, 0) * 2.5
          + s.get(<span class="st">"late_game_foul_rate"</span>, 0) * 1.8
          - s.get(<span class="st">"suspension_cover_score"</span>, 0) * 0.9)

<span class="kw">def</span> <span class="fn">compute_srr</span>(bench: list) -> float:
    <span class="cm"># SRR = feature[22]: weighted bench skill-vector average</span>
    weights = {<span class="st">"GK"</span>:.15,<span class="st">"CB"</span>:.15,<span class="st">"FB"</span>:.10,<span class="st">"CDM"</span>:.15,<span class="st">"CM"</span>:.15,<span class="st">"CAM"</span>:.10,<span class="st">"W"</span>:.10,<span class="st">"ST"</span>:.10}
    <span class="kw">return</span> sum(p[<span class="st">"rating"</span>] * weights.get(p[<span class="st">"pos"</span>], .10) <span class="kw">for</span> p <span class="kw">in</span> bench)

<span class="kw">def</span> <span class="fn">align_schemas</span>(fifa_df, fs_records) -> pd.DataFrame:
    fs_names = [r[<span class="st">"name"</span>] <span class="kw">for</span> r <span class="kw">in</span> fs_records]
    rows = []
    <span class="kw">for</span> _, row <span class="kw">in</span> fifa_df.iterrows():
        match, score, _ = rfuzz.extractOne(row[<span class="st">"name"</span>], fs_names)
        <span class="kw">if</span> score >= 88:  <span class="cm"># RapidFuzz threshold</span>
            fs = fs_records[fs_names.index(match)]
            rows.append({**row, **fs, <span class="st">"pdv"</span>: <span class="fn">compute_pdv</span>(fs), <span class="st">"srr"</span>: <span class="fn">compute_srr</span>(fs.get(<span class="st">"bench"</span>, []))})
    <span class="kw">return</span> pd.DataFrame(rows)</div>

    <div class="code-section-label">2 · PyTorch MatchMLP — 23 features → 3 outcomes</div>
    <div class="codeblock"><span class="kw">import</span> torch, torch.nn <span class="kw">as</span> nn
<span class="kw">from</span> sklearn.preprocessing <span class="kw">import</span> StandardScaler

<span class="kw">class</span> <span class="fn">MatchMLP</span>(nn.Module):
    <span class="kw">def</span> <span class="fn">__init__</span>(self, n=23):
        <span class="kw">super()</span>.__init__()
        self.net = nn.Sequential(
            nn.Linear(n, 256), nn.BatchNorm1d(256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64), nn.BatchNorm1d(64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 3))  <span class="cm"># [win, draw, loss]</span>
    <span class="kw">def</span> <span class="fn">forward</span>(self, x): <span class="kw">return</span> self.net(x)

<span class="kw">def</span> <span class="fn">train_model</span>(X_train, y_train, epochs=80):
    scaler = StandardScaler().fit(X_train)
    Xt = torch.FloatTensor(scaler.transform(X_train))
    yt = torch.LongTensor(y_train)
    loader = DataLoader(TensorDataset(Xt, yt), batch_size=128, shuffle=True)
    model = <span class="fn">MatchMLP</span>()
    optim = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optim, patience=5)
    criterion = nn.CrossEntropyLoss()
    best_val, best_state = float(<span class="st">"inf"</span>), None
    <span class="kw">for</span> ep <span class="kw">in</span> range(epochs):
        model.train(); ep_loss = 0
        <span class="kw">for</span> xb, yb <span class="kw">in</span> loader:
            optim.zero_grad(); loss = criterion(model(xb), yb)
            loss.backward(); optim.step(); ep_loss += loss.item()
        scheduler.step(ep_loss)
        <span class="kw">if</span> ep_loss < best_val: best_val = ep_loss; best_state = model.state_dict()
    model.load_state_dict(best_state)
    <span class="kw">return</span> model, scaler</div>

    <div class="code-section-label">3 · PDV Cascade + Monte Carlo WC 2026 Simulator</div>
    <div class="codeblock"><span class="kw">def</span> <span class="fn">apply_roster_penalties</span>(teams_df, injuries: dict) -> pd.DataFrame:
    <span class="cm"># injuries = {"BRA": ["vinicius"], "ARG": ["di_maria"]}</span>
    df = teams_df.copy()
    <span class="kw">for</span> team_id, players <span class="kw">in</span> injuries.items():
        <span class="kw">for</span> p <span class="kw">in</span> players:
            rating_loss = PLAYER_RATINGS.get(p, 80)
            df.loc[df.team_id==team_id, <span class="st">"xg"</span>] -= (rating_loss - 70) * 0.018
            df.loc[df.team_id==team_id, <span class="st">"srr"</span>] -= (rating_loss - 70) * 0.25
    <span class="kw">return</span> df

<span class="kw">def</span> <span class="fn">pdv_cascade</span>(team, ko_round: int) -> float:
    <span class="cm"># Suspension risk compounds with tournament depth</span>
    base_susp = min(0.85, team[<span class="st">"pdv"</span>] * 0.12 * ko_round)
    <span class="kw">return</span> max(0.60, 1.0 - base_susp * 0.14)

<span class="kw">def</span> <span class="fn">run_wc2026</span>(teams_df, model, scaler, injuries={}, n_sim=10000):
    teams_df = <span class="fn">apply_roster_penalties</span>(teams_df, injuries)
    champ_counts = {}
    <span class="kw">for</span> _ <span class="kw">in</span> range(n_sim):
        qualified = []
        <span class="kw">for</span> grp <span class="kw">in</span> get_groups(teams_df):   <span class="cm"># 12 groups of 4</span>
            pts = {t.team_id: 0 <span class="kw">for</span> t <span class="kw">in</span> grp}
            <span class="kw">for</span> a, b <span class="kw">in</span> [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]:
                p = predict(model, scaler, grp[a], grp[b])
                r = np.random.choice([0, 1, 2], p=p)
                <span class="kw">if</span> r == 0: pts[grp[a].team_id] += 3
                <span class="kw">elif</span> r == 1: pts[grp[a].team_id] += 1; pts[grp[b].team_id] += 1
                <span class="kw">else</span>: pts[grp[b].team_id] += 3
            qualified += sorted(grp, key=<span class="kw">lambda</span> t: -pts[t.team_id])[:2]
        bracket = qualified
        <span class="kw">for</span> ko_round, rnd <span class="kw">in</span> enumerate([<span class="st">"R32"</span>,<span class="st">"R16"</span>,<span class="st">"QF"</span>,<span class="st">"SF"</span>,<span class="st">"Final"</span>], 1):
            nxt = []
            <span class="kw">for</span> i <span class="kw">in</span> range(0, len(bracket), 2):
                a, b = bracket[i], bracket[i+1]
                xg_a = a.xg * <span class="fn">pdv_cascade</span>(a, ko_round)
                xg_b = b.xg * <span class="fn">pdv_cascade</span>(b, ko_round)
                p = predict_adj(model, scaler, a, b, xg_a, xg_b)
                w = a <span class="kw">if</span> np.random.random() < p[0]/(p[0]+p[2]) <span class="kw">else</span> b
                nxt.append(w)
            bracket = nxt
        champ_counts[bracket[0].name] = champ_counts.get(bracket[0].name, 0) + 1
    <span class="kw">return</span> {k: v/n_sim <span class="kw">for</span> k,v <span class="kw">in</span> sorted(champ_counts.items(), key=<span class="kw">lambda</span> x: -x[1])}</div>
  `
}

/* ── API Panel ── */
export function renderAPI(endpoints, credits) {
  const eps = (endpoints || []).map((e, i) => `
    <div class="ep-item">
      <div class="ep-header" data-ep="${i}">
        <span class="method-badge method-${e.method}">${e.method}</span>
        <span class="ep-path">${e.path}</span>
        <span class="ep-desc">${e.desc} · ${e.credits_per_call}cr</span>
      </div>
      <div class="ep-body" id="epb-${i}">// ${e.desc}\n// Cost: ${e.credits_per_call} credits/call\n// See /docs for full Swagger UI</div>
    </div>`).join('')

  return `
    <div class="kicker">Pillar 4 · Commercial Architecture</div>
    <div class="panel-title">FieldIQ API — Burst-Credit Model</div>

    <div class="pricing-grid">
      <div class="price-card">
        <div class="price-tier">Analyst</div>
        <div class="price-amount">$49</div>
        <div class="price-unit">/month</div>
        <div class="price-features">5,000 credits<br>Synergy + PDV<br>CSV export</div>
      </div>
      <div class="price-card featured">
        <div class="price-tier" style="color:var(--lime)">⚡ Pro</div>
        <div class="price-amount">$199</div>
        <div class="price-unit">/month</div>
        <div class="price-features">25,000 credits<br>All endpoints<br>Cascade + SRR<br>Webhooks</div>
      </div>
      <div class="price-card">
        <div class="price-tier">Enterprise</div>
        <div class="price-amount" style="font-size:.95rem;padding-top:.3rem">Custom</div>
        <div class="price-unit"> </div>
        <div class="price-features">Unlimited burst<br>White-label<br>SLA + support</div>
      </div>
    </div>

    ${credits ? `
    <div class="card card-l">
      <div class="card-title">Live Credit Pool — Pro Tier</div>
      <div class="metrics">
        <div class="met"><div class="met-val g">${credits.credits_remaining.toLocaleString()}</div><div class="met-lbl">Remaining</div></div>
        <div class="met"><div class="met-val a">${credits.credits_used.toLocaleString()}</div><div class="met-lbl">Used</div></div>
        <div class="met"><div class="met-val s">${credits.rollover_banked}</div><div class="met-lbl">Rollover</div></div>
        <div class="met"><div class="met-val r">${credits.burst_lane}</div><div class="met-lbl">Burst Lane</div></div>
      </div>
    </div>` : ''}

    <div class="card card-s">
      <div class="card-title">Endpoints <small style="font-weight:400;color:var(--muted);font-size:10px">— click to expand · full docs at <a href="/docs" style="color:var(--sky)">/docs</a></small></div>
      ${eps}
    </div>

    <div class="card card-l" style="font-family:var(--font-mono);font-size:10px;line-height:1.8;color:rgba(184,242,65,.75)">
      <div class="kicker">Matrix Ingestion — single POST, full output</div>
      POST /v1/tournament/simulate<br>
      <span style="color:var(--muted)">{ "n_simulations": 1000, "elo_weight": 0.40, "pdv_weight": 0.20,</span><br>
      <span style="color:var(--muted)">&nbsp;&nbsp;"srr_weight": 0.10, "injuries": {"BRA": ["vinicius"]} }</span><br><br>
      <span style="color:var(--muted)">→ champion_probs{}, group_results[], ko_results{},</span><br>
      <span style="color:var(--muted)">→ display_champion{}, display_finalist_a{}, display_finalist_b{}</span>
    </div>

    <div class="alert alert-lime">
      <span>💡</span>
      <div><strong>Burst vs FootyStats</strong>
        FootyStats hard-blocks at daily API call limits. FieldIQ credits pool monthly — burn 3× on match
        days, recover mid-week. Enterprise gets guaranteed burst lanes for final-day spikes.</div>
    </div>
  `
}

/* ── Helpers ── */
export function pdvColor(v) {
  return v > 2.0 ? 'var(--red)' : v > 1.3 ? 'var(--amber)' : 'var(--lime)'
}

function slider(id, label, val) {
  return `
    <div class="sl-row">
      <label>${label}</label>
      <input type="range" min="0" max="100" value="${val}" id="${id}" step="1"
             oninput="document.getElementById('${id}v').textContent=this.value+'%'">
      <span class="sl-val" id="${id}v">${val}%</span>
    </div>`
}

function triStat(label, val, cls) {
  return `
    <div style="background:var(--ink3);border:1px solid var(--border);border-radius:7px;padding:.7rem;text-align:center">
      <div style="font-family:var(--font-ui);font-size:9px;font-weight:700;color:var(--muted);text-transform:uppercase;margin-bottom:.25rem">${label}</div>
      <div style="font-family:var(--font-ui);font-size:1.4rem;font-weight:800" class="met-val ${cls}">${val}</div>
    </div>`
}
