const BASE = '/v1'

async function req(method, path, body = null) {
  const opts = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'demo',
    },
  }
  if (body) opts.body = JSON.stringify(body)
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error || err.detail?.error || `${res.status} ${res.statusText}`)
  }
  return res.json()
}

export const api = {
  health:         ()       => fetch('/health').then(r => r.json()),
  simulate:       (body)   => req('POST', '/tournament/simulate', body),
  teams:          ()       => req('GET',  '/tournament/teams'),
  synergy:        (body)   => req('POST', '/squad/synergy', body),
  players:        (tid)    => req('GET',  `/squad/players/${tid}`),
  pdvScores:      ()       => req('GET',  '/pdv/scores'),
  pdvCascade:     (body)   => req('POST', '/pdv/cascade', body),
  pdvFormula:     ()       => req('GET',  '/pdv/formula'),
  srrRankings:    (sc)     => req('GET',  `/srr/rankings?scenario=${sc}`),
  srrAll:         ()       => req('GET',  '/srr/all'),
  modelArch:      ()       => req('GET',  '/model/architecture'),
  modelRankings:  ()       => req('GET',  '/model/rankings'),
  credits:        ()       => req('GET',  '/credits/balance?tier=pro'),
  endpoints:      ()       => req('GET',  '/credits/endpoints'),
  fatigue:        (tid, n) => req('GET',  `/v3/fatigue/${tid}?match_number=${n}`),
  fullAnalysis:   (body)   => req('POST', '/v3/full-analysis', body),
  dataSources:    ()       => req('GET',  '/model/data-sources'),
}
