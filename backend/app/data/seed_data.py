"""
Seed data for WC 2026 teams and players.
Production path: app/data_pipeline/live_adapters.py (multi-provider ingestion).
"""

from typing import Dict, List, Optional

TEAMS: List[Dict] = [
    {"id":"BRA","name":"Brazil","flag":"🇧🇷","elo":2091,"xg":2.3,"xga":1.1,"form":78,"pdv":1.2,"rank":1,"srr":71,"wc_titles":5,"wc_apps":22,"qual_pts":38,"squad_age":26.4,"caps_avg":44,"ppda":9.2,"deep_comp":52,"shot_acc":0.38,"set_piece":0.11,"aerial":0.61,"confederation":"CONMEBOL"},
    {"id":"FRA","name":"France","flag":"🇫🇷","elo":2005,"xg":2.1,"xga":1.0,"form":75,"pdv":1.8,"rank":2,"srr":88,"wc_titles":2,"wc_apps":16,"qual_pts":35,"squad_age":27.1,"caps_avg":52,"ppda":8.8,"deep_comp":55,"shot_acc":0.37,"set_piece":0.13,"aerial":0.57,"confederation":"UEFA"},
    {"id":"ENG","name":"England","flag":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","elo":1983,"xg":2.0,"xga":1.2,"form":72,"pdv":1.5,"rank":3,"srr":79,"wc_titles":1,"wc_apps":16,"qual_pts":33,"squad_age":26.8,"caps_avg":38,"ppda":9.5,"deep_comp":50,"shot_acc":0.35,"set_piece":0.14,"aerial":0.59,"confederation":"UEFA"},
    {"id":"ARG","name":"Argentina","flag":"🇦🇷","elo":1975,"xg":1.9,"xga":1.1,"form":80,"pdv":2.1,"rank":4,"srr":58,"wc_titles":3,"wc_apps":18,"qual_pts":37,"squad_age":28.2,"caps_avg":61,"ppda":10.1,"deep_comp":48,"shot_acc":0.34,"set_piece":0.12,"aerial":0.58,"confederation":"CONMEBOL"},
    {"id":"ESP","name":"Spain","flag":"🇪🇸","elo":1967,"xg":2.2,"xga":0.9,"form":71,"pdv":1.4,"rank":5,"srr":84,"wc_titles":1,"wc_apps":15,"qual_pts":32,"squad_age":25.6,"caps_avg":35,"ppda":7.9,"deep_comp":58,"shot_acc":0.41,"set_piece":0.10,"aerial":0.52,"confederation":"UEFA"},
    {"id":"POR","name":"Portugal","flag":"🇵🇹","elo":1950,"xg":1.8,"xga":1.1,"form":69,"pdv":1.6,"rank":6,"srr":45,"wc_titles":0,"wc_apps":8,"qual_pts":30,"squad_age":27.8,"caps_avg":48,"ppda":9.8,"deep_comp":47,"shot_acc":0.36,"set_piece":0.12,"aerial":0.60,"confederation":"UEFA"},
    {"id":"GER","name":"Germany","flag":"🇩🇪","elo":1930,"xg":1.7,"xga":1.3,"form":65,"pdv":1.3,"rank":7,"srr":82,"wc_titles":4,"wc_apps":20,"qual_pts":29,"squad_age":26.1,"caps_avg":40,"ppda":9.1,"deep_comp":53,"shot_acc":0.36,"set_piece":0.11,"aerial":0.62,"confederation":"UEFA"},
    {"id":"NED","name":"Netherlands","flag":"🇳🇱","elo":1920,"xg":1.85,"xga":1.2,"form":68,"pdv":1.7,"rank":8,"srr":73,"wc_titles":0,"wc_apps":11,"qual_pts":28,"squad_age":26.5,"caps_avg":37,"ppda":9.4,"deep_comp":51,"shot_acc":0.37,"set_piece":0.12,"aerial":0.60,"confederation":"UEFA"},
    {"id":"BEL","name":"Belgium","flag":"🇧🇪","elo":1905,"xg":1.75,"xga":1.3,"form":63,"pdv":1.9,"rank":9,"srr":66,"wc_titles":0,"wc_apps":13,"qual_pts":26,"squad_age":29.1,"caps_avg":55,"ppda":10.2,"deep_comp":46,"shot_acc":0.34,"set_piece":0.11,"aerial":0.61,"confederation":"UEFA"},
    {"id":"URU","name":"Uruguay","flag":"🇺🇾","elo":1890,"xg":1.6,"xga":1.2,"form":66,"pdv":2.3,"rank":10,"srr":61,"wc_titles":2,"wc_apps":14,"qual_pts":27,"squad_age":27.6,"caps_avg":50,"ppda":10.8,"deep_comp":44,"shot_acc":0.33,"set_piece":0.10,"aerial":0.64,"confederation":"CONMEBOL"},
    {"id":"CRO","name":"Croatia","flag":"🇭🇷","elo":1870,"xg":1.55,"xga":1.3,"form":64,"pdv":1.8,"rank":11,"srr":68,"wc_titles":0,"wc_apps":6,"qual_pts":25,"squad_age":30.2,"caps_avg":58,"ppda":10.5,"deep_comp":43,"shot_acc":0.32,"set_piece":0.10,"aerial":0.59,"confederation":"UEFA"},
    {"id":"ITA","name":"Italy","flag":"🇮🇹","elo":1860,"xg":1.65,"xga":1.1,"form":60,"pdv":1.6,"rank":12,"srr":75,"wc_titles":4,"wc_apps":18,"qual_pts":24,"squad_age":27.3,"caps_avg":42,"ppda":9.7,"deep_comp":49,"shot_acc":0.35,"set_piece":0.11,"aerial":0.58,"confederation":"UEFA"},
    {"id":"MAR","name":"Morocco","flag":"🇲🇦","elo":1840,"xg":1.5,"xga":1.0,"form":67,"pdv":1.4,"rank":13,"srr":70,"wc_titles":0,"wc_apps":6,"qual_pts":26,"squad_age":26.9,"caps_avg":34,"ppda":10.3,"deep_comp":45,"shot_acc":0.33,"set_piece":0.09,"aerial":0.63,"confederation":"CAF"},
    {"id":"USA","name":"USA","flag":"🇺🇸","elo":1820,"xg":1.55,"xga":1.4,"form":62,"pdv":1.5,"rank":14,"srr":72,"wc_titles":0,"wc_apps":11,"qual_pts":23,"squad_age":25.2,"caps_avg":28,"ppda":10.0,"deep_comp":47,"shot_acc":0.34,"set_piece":0.10,"aerial":0.56,"confederation":"CONCACAF"},
    {"id":"MEX","name":"Mexico","flag":"🇲🇽","elo":1800,"xg":1.45,"xga":1.4,"form":58,"pdv":2.0,"rank":15,"srr":64,"wc_titles":0,"wc_apps":17,"qual_pts":21,"squad_age":27.0,"caps_avg":39,"ppda":10.6,"deep_comp":44,"shot_acc":0.32,"set_piece":0.09,"aerial":0.55,"confederation":"CONCACAF"},
    {"id":"COL","name":"Colombia","flag":"🇨🇴","elo":1790,"xg":1.5,"xga":1.3,"form":61,"pdv":2.1,"rank":16,"srr":60,"wc_titles":0,"wc_apps":6,"qual_pts":22,"squad_age":27.4,"caps_avg":36,"ppda":10.4,"deep_comp":43,"shot_acc":0.33,"set_piece":0.10,"aerial":0.58,"confederation":"CONMEBOL"},
    # ── Additional 32 teams for full 48-team bracket ──
    {"id":"SEN","name":"Senegal","flag":"🇸🇳","elo":1770,"xg":1.4,"xga":1.3,"form":60,"pdv":1.6,"rank":17,"srr":62,"wc_titles":0,"wc_apps":3,"qual_pts":20,"squad_age":26.1,"caps_avg":32,"ppda":11.2,"deep_comp":41,"shot_acc":0.31,"set_piece":0.09,"aerial":0.64,"confederation":"CAF"},
    {"id":"JPN","name":"Japan","flag":"🇯🇵","elo":1760,"xg":1.45,"xga":1.2,"form":63,"pdv":0.9,"rank":18,"srr":67,"wc_titles":0,"wc_apps":7,"qual_pts":22,"squad_age":25.8,"caps_avg":30,"ppda":9.8,"deep_comp":48,"shot_acc":0.35,"set_piece":0.10,"aerial":0.48,"confederation":"AFC"},
    {"id":"AUS","name":"Australia","flag":"🇦🇺","elo":1730,"xg":1.3,"xga":1.4,"form":58,"pdv":1.2,"rank":19,"srr":58,"wc_titles":0,"wc_apps":5,"qual_pts":18,"squad_age":26.5,"caps_avg":28,"ppda":11.5,"deep_comp":39,"shot_acc":0.30,"set_piece":0.09,"aerial":0.62,"confederation":"AFC"},
    {"id":"KOR","name":"South Korea","flag":"🇰🇷","elo":1720,"xg":1.35,"xga":1.4,"form":57,"pdv":1.3,"rank":20,"srr":60,"wc_titles":0,"wc_apps":11,"qual_pts":19,"squad_age":26.2,"caps_avg":35,"ppda":10.8,"deep_comp":42,"shot_acc":0.32,"set_piece":0.09,"aerial":0.55,"confederation":"AFC"},
    {"id":"IRN","name":"Iran","flag":"🇮🇷","elo":1710,"xg":1.2,"xga":1.3,"form":56,"pdv":1.5,"rank":21,"srr":55,"wc_titles":0,"wc_apps":6,"qual_pts":17,"squad_age":27.1,"caps_avg":31,"ppda":11.8,"deep_comp":38,"shot_acc":0.29,"set_piece":0.08,"aerial":0.65,"confederation":"AFC"},
    {"id":"SAU","name":"Saudi Arabia","flag":"🇸🇦","elo":1700,"xg":1.25,"xga":1.5,"form":55,"pdv":1.4,"rank":22,"srr":54,"wc_titles":0,"wc_apps":6,"qual_pts":16,"squad_age":26.8,"caps_avg":29,"ppda":12.1,"deep_comp":37,"shot_acc":0.28,"set_piece":0.08,"aerial":0.62,"confederation":"AFC"},
    {"id":"ECU","name":"Ecuador","flag":"🇪🇨","elo":1750,"xg":1.4,"xga":1.3,"form":59,"pdv":1.7,"rank":23,"srr":59,"wc_titles":0,"wc_apps":4,"qual_pts":21,"squad_age":25.9,"caps_avg":27,"ppda":11.0,"deep_comp":40,"shot_acc":0.31,"set_piece":0.09,"aerial":0.60,"confederation":"CONMEBOL"},
    {"id":"CHI","name":"Chile","flag":"🇨🇱","elo":1740,"xg":1.35,"xga":1.4,"form":57,"pdv":1.9,"rank":24,"srr":57,"wc_titles":0,"wc_apps":9,"qual_pts":19,"squad_age":28.4,"caps_avg":42,"ppda":10.9,"deep_comp":41,"shot_acc":0.30,"set_piece":0.09,"aerial":0.58,"confederation":"CONMEBOL"},
    {"id":"SUI","name":"Switzerland","flag":"🇨🇭","elo":1800,"xg":1.5,"xga":1.2,"form":61,"pdv":1.3,"rank":25,"srr":69,"wc_titles":0,"wc_apps":11,"qual_pts":23,"squad_age":27.2,"caps_avg":38,"ppda":9.9,"deep_comp":46,"shot_acc":0.33,"set_piece":0.10,"aerial":0.59,"confederation":"UEFA"},
    {"id":"DEN","name":"Denmark","flag":"🇩🇰","elo":1810,"xg":1.55,"xga":1.1,"form":63,"pdv":1.2,"rank":26,"srr":71,"wc_titles":0,"wc_apps":5,"qual_pts":24,"squad_age":27.0,"caps_avg":36,"ppda":9.6,"deep_comp":47,"shot_acc":0.34,"set_piece":0.11,"aerial":0.61,"confederation":"UEFA"},
    {"id":"POL","name":"Poland","flag":"🇵🇱","elo":1760,"xg":1.4,"xga":1.3,"form":58,"pdv":1.6,"rank":27,"srr":63,"wc_titles":0,"wc_apps":9,"qual_pts":20,"squad_age":27.8,"caps_avg":40,"ppda":11.1,"deep_comp":42,"shot_acc":0.31,"set_piece":0.10,"aerial":0.63,"confederation":"UEFA"},
    {"id":"UKR","name":"Ukraine","flag":"🇺🇦","elo":1750,"xg":1.35,"xga":1.3,"form":57,"pdv":1.4,"rank":28,"srr":61,"wc_titles":0,"wc_apps":2,"qual_pts":19,"squad_age":27.5,"caps_avg":38,"ppda":10.7,"deep_comp":43,"shot_acc":0.32,"set_piece":0.10,"aerial":0.60,"confederation":"UEFA"},
    {"id":"TUR","name":"Turkey","flag":"🇹🇷","elo":1740,"xg":1.4,"xga":1.4,"form":59,"pdv":1.8,"rank":29,"srr":62,"wc_titles":0,"wc_apps":2,"qual_pts":21,"squad_age":26.9,"caps_avg":35,"ppda":10.5,"deep_comp":44,"shot_acc":0.32,"set_piece":0.09,"aerial":0.62,"confederation":"UEFA"},
    {"id":"SWE","name":"Sweden","flag":"🇸🇪","elo":1730,"xg":1.35,"xga":1.3,"form":57,"pdv":1.3,"rank":30,"srr":64,"wc_titles":0,"wc_apps":12,"qual_pts":18,"squad_age":27.3,"caps_avg":37,"ppda":10.8,"deep_comp":43,"shot_acc":0.31,"set_piece":0.10,"aerial":0.61,"confederation":"UEFA"},
    {"id":"CAN","name":"Canada","flag":"🇨🇦","elo":1690,"xg":1.3,"xga":1.5,"form":54,"pdv":1.4,"rank":31,"srr":58,"wc_titles":0,"wc_apps":2,"qual_pts":16,"squad_age":24.8,"caps_avg":28,"ppda":11.8,"deep_comp":38,"shot_acc":0.29,"set_piece":0.08,"aerial":0.54,"confederation":"CONCACAF"},
    {"id":"CRC","name":"Costa Rica","flag":"🇨🇷","elo":1680,"xg":1.2,"xga":1.5,"form":53,"pdv":1.5,"rank":32,"srr":55,"wc_titles":0,"wc_apps":6,"qual_pts":15,"squad_age":28.1,"caps_avg":33,"ppda":12.0,"deep_comp":37,"shot_acc":0.28,"set_piece":0.08,"aerial":0.60,"confederation":"CONCACAF"},
    {"id":"CMR","name":"Cameroon","flag":"🇨🇲","elo":1720,"xg":1.3,"xga":1.4,"form":56,"pdv":1.8,"rank":33,"srr":57,"wc_titles":0,"wc_apps":8,"qual_pts":17,"squad_age":27.2,"caps_avg":30,"ppda":11.5,"deep_comp":39,"shot_acc":0.30,"set_piece":0.08,"aerial":0.66,"confederation":"CAF"},
    {"id":"GHA","name":"Ghana","flag":"🇬🇭","elo":1700,"xg":1.25,"xga":1.4,"form":55,"pdv":1.9,"rank":34,"srr":56,"wc_titles":0,"wc_apps":4,"qual_pts":16,"squad_age":27.4,"caps_avg":28,"ppda":11.8,"deep_comp":38,"shot_acc":0.29,"set_piece":0.08,"aerial":0.63,"confederation":"CAF"},
    {"id":"NGA","name":"Nigeria","flag":"🇳🇬","elo":1710,"xg":1.35,"xga":1.4,"form":57,"pdv":1.7,"rank":35,"srr":58,"wc_titles":0,"wc_apps":6,"qual_pts":17,"squad_age":26.8,"caps_avg":32,"ppda":11.3,"deep_comp":40,"shot_acc":0.30,"set_piece":0.09,"aerial":0.64,"confederation":"CAF"},
    {"id":"EGY","name":"Egypt","flag":"🇪🇬","elo":1690,"xg":1.2,"xga":1.3,"form":55,"pdv":1.6,"rank":36,"srr":57,"wc_titles":0,"wc_apps":3,"qual_pts":16,"squad_age":27.1,"caps_avg":29,"ppda":11.6,"deep_comp":39,"shot_acc":0.29,"set_piece":0.09,"aerial":0.62,"confederation":"CAF"},
    {"id":"QAT","name":"Qatar","flag":"🇶🇦","elo":1660,"xg":1.1,"xga":1.6,"form":50,"pdv":1.3,"rank":37,"srr":52,"wc_titles":0,"wc_apps":1,"qual_pts":12,"squad_age":26.5,"caps_avg":24,"ppda":12.5,"deep_comp":34,"shot_acc":0.27,"set_piece":0.07,"aerial":0.57,"confederation":"AFC"},
    {"id":"PAR","name":"Paraguay","flag":"🇵🇾","elo":1680,"xg":1.2,"xga":1.5,"form":52,"pdv":2.0,"rank":38,"srr":54,"wc_titles":0,"wc_apps":8,"qual_pts":14,"squad_age":27.0,"caps_avg":30,"ppda":11.9,"deep_comp":37,"shot_acc":0.28,"set_piece":0.08,"aerial":0.61,"confederation":"CONMEBOL"},
    {"id":"BOL","name":"Bolivia","flag":"🇧🇴","elo":1650,"xg":1.1,"xga":1.7,"form":48,"pdv":1.8,"rank":39,"srr":50,"wc_titles":0,"wc_apps":3,"qual_pts":11,"squad_age":26.2,"caps_avg":26,"ppda":12.8,"deep_comp":33,"shot_acc":0.26,"set_piece":0.07,"aerial":0.60,"confederation":"CONMEBOL"},
    {"id":"ROM","name":"Romania","flag":"🇷🇴","elo":1710,"xg":1.3,"xga":1.4,"form":56,"pdv":1.5,"rank":40,"srr":60,"wc_titles":0,"wc_apps":7,"qual_pts":18,"squad_age":26.7,"caps_avg":32,"ppda":11.2,"deep_comp":41,"shot_acc":0.30,"set_piece":0.09,"aerial":0.60,"confederation":"UEFA"},
    {"id":"AUT","name":"Austria","flag":"🇦🇹","elo":1730,"xg":1.4,"xga":1.3,"form":58,"pdv":1.4,"rank":41,"srr":62,"wc_titles":0,"wc_apps":7,"qual_pts":19,"squad_age":26.4,"caps_avg":33,"ppda":10.9,"deep_comp":43,"shot_acc":0.31,"set_piece":0.09,"aerial":0.59,"confederation":"UEFA"},
    {"id":"SCO","name":"Scotland","flag":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","elo":1700,"xg":1.3,"xga":1.4,"form":55,"pdv":1.5,"rank":42,"srr":59,"wc_titles":0,"wc_apps":8,"qual_pts":17,"squad_age":27.1,"caps_avg":31,"ppda":10.8,"deep_comp":41,"shot_acc":0.30,"set_piece":0.09,"aerial":0.61,"confederation":"UEFA"},
    {"id":"HUN","name":"Hungary","flag":"🇭🇺","elo":1680,"xg":1.2,"xga":1.5,"form":52,"pdv":1.6,"rank":43,"srr":57,"wc_titles":0,"wc_apps":9,"qual_pts":15,"squad_age":27.5,"caps_avg":34,"ppda":11.4,"deep_comp":39,"shot_acc":0.29,"set_piece":0.09,"aerial":0.62,"confederation":"UEFA"},
    {"id":"GRE","name":"Greece","flag":"🇬🇷","elo":1670,"xg":1.15,"xga":1.5,"form":51,"pdv":1.4,"rank":44,"srr":56,"wc_titles":0,"wc_apps":3,"qual_pts":14,"squad_age":28.0,"caps_avg":35,"ppda":11.6,"deep_comp":38,"shot_acc":0.29,"set_piece":0.08,"aerial":0.63,"confederation":"UEFA"},
    {"id":"SRB","name":"Serbia","flag":"🇷🇸","elo":1750,"xg":1.4,"xga":1.3,"form":58,"pdv":1.7,"rank":45,"srr":61,"wc_titles":0,"wc_apps":3,"qual_pts":20,"squad_age":27.3,"caps_avg":36,"ppda":10.8,"deep_comp":42,"shot_acc":0.31,"set_piece":0.10,"aerial":0.61,"confederation":"UEFA"},
    {"id":"CZE","name":"Czech Rep.","flag":"🇨🇿","elo":1720,"xg":1.3,"xga":1.4,"form":56,"pdv":1.3,"rank":46,"srr":60,"wc_titles":0,"wc_apps":9,"qual_pts":17,"squad_age":27.2,"caps_avg":33,"ppda":11.0,"deep_comp":41,"shot_acc":0.30,"set_piece":0.09,"aerial":0.60,"confederation":"UEFA"},
    {"id":"PER","name":"Peru","flag":"🇵🇪","elo":1700,"xg":1.3,"xga":1.4,"form":54,"pdv":1.6,"rank":47,"srr":58,"wc_titles":0,"wc_apps":5,"qual_pts":16,"squad_age":28.5,"caps_avg":38,"ppda":11.3,"deep_comp":40,"shot_acc":0.30,"set_piece":0.09,"aerial":0.59,"confederation":"CONMEBOL"},
    {"id":"VEN","name":"Venezuela","flag":"🇻🇪","elo":1690,"xg":1.2,"xga":1.5,"form":52,"pdv":1.7,"rank":48,"srr":55,"wc_titles":0,"wc_apps":0,"qual_pts":14,"squad_age":25.9,"caps_avg":23,"ppda":11.8,"deep_comp":37,"shot_acc":0.28,"set_piece":0.08,"aerial":0.58,"confederation":"CONMEBOL"},
]

PLAYERS: List[Dict] = [
    {"id":"alisson","name":"Alisson","team_id":"BRA","pos":"GK","rating":91,"pdv":0.3,"yellow_per90":0.1,"reds_season":0,"late_foul_rate":0.02,"suspension_cover":0.9},
    {"id":"militao","name":"Militão","team_id":"BRA","pos":"CB","rating":85,"pdv":0.8,"yellow_per90":0.4,"reds_season":0,"late_foul_rate":0.06,"suspension_cover":0.7},
    {"id":"marquinhos","name":"Marquinhos","team_id":"BRA","pos":"CB","rating":88,"pdv":0.7,"yellow_per90":0.3,"reds_season":0,"late_foul_rate":0.05,"suspension_cover":0.8},
    {"id":"silva","name":"T. Silva","team_id":"BRA","pos":"CB","rating":87,"pdv":0.4,"yellow_per90":0.2,"reds_season":0,"late_foul_rate":0.04,"suspension_cover":0.8},
    {"id":"danilo","name":"Danilo","team_id":"BRA","pos":"FB","rating":82,"pdv":1.1,"yellow_per90":0.5,"reds_season":0,"late_foul_rate":0.09,"suspension_cover":0.6},
    {"id":"casemiro","name":"Casemiro","team_id":"BRA","pos":"CDM","rating":86,"pdv":2.4,"yellow_per90":0.9,"reds_season":1,"late_foul_rate":0.18,"suspension_cover":0.5},
    {"id":"paqueta","name":"Paquetá","team_id":"BRA","pos":"CM","rating":84,"pdv":1.2,"yellow_per90":0.6,"reds_season":0,"late_foul_rate":0.10,"suspension_cover":0.6},
    {"id":"guimaraes","name":"Bruno Guimarães","team_id":"BRA","pos":"CM","rating":87,"pdv":0.9,"yellow_per90":0.4,"reds_season":0,"late_foul_rate":0.07,"suspension_cover":0.7},
    {"id":"rodrygo","name":"Rodrygo","team_id":"BRA","pos":"W","rating":83,"pdv":0.6,"yellow_per90":0.3,"reds_season":0,"late_foul_rate":0.05,"suspension_cover":0.7},
    {"id":"vinicius","name":"Vinícius","team_id":"BRA","pos":"W","rating":92,"pdv":1.8,"yellow_per90":0.8,"reds_season":0,"late_foul_rate":0.15,"suspension_cover":0.5},
    {"id":"endrick","name":"Endrick","team_id":"BRA","pos":"ST","rating":81,"pdv":0.5,"yellow_per90":0.2,"reds_season":0,"late_foul_rate":0.04,"suspension_cover":0.7},
]

# Canonical XI template for synthetic squads (teams without explicit player data)
_SQUAD_TEMPLATE = ["GK", "CB", "CB", "CB", "FB", "FB", "CDM", "CM", "CM", "W", "ST"]
_CLUB_POOL = [
    "real_madrid", "man_city", "bayern", "psg", "liverpool",
    "barcelona", "inter", "juventus", "chelsea", "arsenal",
]

PDV_COHORT: List[Dict] = [
    {"player":"Casemiro","team":"🇧🇷 BRA","pdv":2.4,"susp_pct":38,"risk":"HIGH"},
    {"player":"Paredes","team":"🇦🇷 ARG","pdv":2.7,"susp_pct":44,"risk":"HIGH"},
    {"player":"Partey","team":"🇬🇭 GHA","pdv":2.3,"susp_pct":35,"risk":"HIGH"},
    {"player":"Kessié","team":"🇲🇦 MAR","pdv":2.1,"susp_pct":29,"risk":"HIGH"},
    {"player":"Vinícius Jr","team":"🇧🇷 BRA","pdv":1.8,"susp_pct":22,"risk":"MED"},
    {"player":"Tchouameni","team":"🇫🇷 FRA","pdv":1.5,"susp_pct":18,"risk":"MED"},
    {"player":"Bellingham","team":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG","pdv":0.9,"susp_pct":11,"risk":"LOW"},
    {"player":"Modrić","team":"🇭🇷 CRO","pdv":0.6,"susp_pct":7,"risk":"LOW"},
]

SRR_DATA: List[Dict] = [
    {"flag":"🇫🇷","name":"France","srr":{"striker":88,"mid":91,"def":85,"gk":78},"delta":{"striker":-3,"mid":-5,"def":-8,"gk":-15}},
    {"flag":"🇧🇷","name":"Brazil","srr":{"striker":71,"mid":83,"def":80,"gk":62},"delta":{"striker":-18,"mid":-9,"def":-12,"gk":-22}},
    {"flag":"🇪🇸","name":"Spain","srr":{"striker":84,"mid":92,"def":87,"gk":80},"delta":{"striker":-7,"mid":-4,"def":-6,"gk":-11}},
    {"flag":"🇦🇷","name":"Argentina","srr":{"striker":58,"mid":76,"def":78,"gk":71},"delta":{"striker":-28,"mid":-14,"def":-10,"gk":-13}},
    {"flag":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","name":"England","srr":{"striker":79,"mid":81,"def":83,"gk":85},"delta":{"striker":-12,"mid":-11,"def":-9,"gk":-8}},
    {"flag":"🇵🇹","name":"Portugal","srr":{"striker":45,"mid":68,"def":72,"gk":74},"delta":{"striker":-35,"mid":-20,"def":-15,"gk":-12}},
]

# ── V3 tactical and chemistry extension data ──────────────────────────────
# Augments the 16 top teams with fields needed by the four new engines.
# def_line_height:              0=deep block, 1=very high line
# winger_sprint_pace:           0-1 normalised sprint speed of wide attackers
# pass_completion_pressure:     pass completion rate under pressing situations
# crosses_per_90 / aerial_duel_win_pct: xT winger-striker compatibility fields

V3_TEAM_EXTENSIONS: dict = {
    "BRA": {"def_line_height": 0.58, "winger_sprint_pace": 0.88, "pass_completion_pressure": 0.64},
    "FRA": {"def_line_height": 0.62, "winger_sprint_pace": 0.80, "pass_completion_pressure": 0.68},
    "ENG": {"def_line_height": 0.70, "winger_sprint_pace": 0.75, "pass_completion_pressure": 0.60},
    "ARG": {"def_line_height": 0.52, "winger_sprint_pace": 0.78, "pass_completion_pressure": 0.62},
    "ESP": {"def_line_height": 0.75, "winger_sprint_pace": 0.72, "pass_completion_pressure": 0.74},  # tiki-taka press resistance
    "POR": {"def_line_height": 0.55, "winger_sprint_pace": 0.82, "pass_completion_pressure": 0.65},
    "GER": {"def_line_height": 0.68, "winger_sprint_pace": 0.76, "pass_completion_pressure": 0.66},
    "NED": {"def_line_height": 0.72, "winger_sprint_pace": 0.77, "pass_completion_pressure": 0.63},
    "BEL": {"def_line_height": 0.55, "winger_sprint_pace": 0.79, "pass_completion_pressure": 0.61},
    "URU": {"def_line_height": 0.45, "winger_sprint_pace": 0.71, "pass_completion_pressure": 0.58},
    "CRO": {"def_line_height": 0.50, "winger_sprint_pace": 0.68, "pass_completion_pressure": 0.67},
    "ITA": {"def_line_height": 0.48, "winger_sprint_pace": 0.74, "pass_completion_pressure": 0.69},
    "MAR": {"def_line_height": 0.42, "winger_sprint_pace": 0.80, "pass_completion_pressure": 0.70},  # low block masters
    "USA": {"def_line_height": 0.60, "winger_sprint_pace": 0.83, "pass_completion_pressure": 0.58},
    "MEX": {"def_line_height": 0.54, "winger_sprint_pace": 0.76, "pass_completion_pressure": 0.62},
    "COL": {"def_line_height": 0.56, "winger_sprint_pace": 0.79, "pass_completion_pressure": 0.60},
}

# Extend TEAMS list with v3 fields
for _t in TEAMS:
    _ext = V3_TEAM_EXTENSIONS.get(_t["id"], {
        "def_line_height": 0.52, "winger_sprint_pace": 0.70, "pass_completion_pressure": 0.60
    })
    _t.update(_ext)

# V3 player extensions: club_id, crosses_per_90, aerial_duel_win_pct, penalty_conversion_rate
V3_PLAYER_EXTENSIONS: dict = {
    "alisson":    {"club_id": "liverpool",       "crosses_per_90": 0.0,  "aerial_duel_win_pct": 0.00, "penalty_conversion_rate": 0.00},
    "militao":    {"club_id": "real_madrid",     "crosses_per_90": 0.3,  "aerial_duel_win_pct": 0.62, "penalty_conversion_rate": 0.70},
    "marquinhos": {"club_id": "paris_sg",        "crosses_per_90": 0.2,  "aerial_duel_win_pct": 0.68, "penalty_conversion_rate": 0.72},
    "silva":      {"club_id": "chelsea",         "crosses_per_90": 0.1,  "aerial_duel_win_pct": 0.71, "penalty_conversion_rate": 0.74},
    "danilo":     {"club_id": "juventus",        "crosses_per_90": 1.8,  "aerial_duel_win_pct": 0.48, "penalty_conversion_rate": 0.68},
    "casemiro":   {"club_id": "man_utd",         "crosses_per_90": 0.4,  "aerial_duel_win_pct": 0.55, "penalty_conversion_rate": 0.73},
    "paqueta":    {"club_id": "west_ham",        "crosses_per_90": 0.9,  "aerial_duel_win_pct": 0.44, "penalty_conversion_rate": 0.76},
    "guimaraes":  {"club_id": "newcastle",       "crosses_per_90": 0.5,  "aerial_duel_win_pct": 0.50, "penalty_conversion_rate": 0.76},
    "rodrygo":    {"club_id": "real_madrid",     "crosses_per_90": 2.1,  "aerial_duel_win_pct": 0.38, "penalty_conversion_rate": 0.77},
    "vinicius":   {"club_id": "real_madrid",     "crosses_per_90": 1.4,  "aerial_duel_win_pct": 0.35, "penalty_conversion_rate": 0.75},
    "endrick":    {"club_id": "real_madrid",     "crosses_per_90": 0.5,  "aerial_duel_win_pct": 0.58, "penalty_conversion_rate": 0.78},
}

# Extend PLAYERS with v3 fields
for _p in PLAYERS:
    _ext = V3_PLAYER_EXTENSIONS.get(_p["id"], {
        "club_id": "unknown", "crosses_per_90": 1.5,
        "aerial_duel_win_pct": 0.50, "penalty_conversion_rate": 0.72,
    })
    _p.update(_ext)


def get_team_squad(team_id: str) -> List[Dict]:
    """Return explicit or synthetic 11-player squad for chemistry/momentum engines."""
    explicit = [dict(p) for p in PLAYERS if p["team_id"] == team_id]
    if explicit:
        return explicit

    team: Optional[Dict] = next((t for t in TEAMS if t["id"] == team_id), None)
    if not team:
        return []

    base_rating = max(65, min(92, int(team["elo"] / 23)))
    pdv_base = team.get("pdv", 1.2)
    squad: List[Dict] = []

    for i, pos in enumerate(_SQUAD_TEMPLATE):
        club = _CLUB_POOL[i % len(_CLUB_POOL)]
        rating = base_rating + (4 if i < 4 else 0) - (2 if pos == "GK" else 0)
        squad.append({
            "id": f"{team_id}_{i}",
            "name": f"{team['name']} #{i + 1}",
            "team_id": team_id,
            "pos": pos,
            "rating": rating,
            "pdv": round(pdv_base * 0.45, 2),
            "club_id": club if i % 3 != 0 else f"{club}_alt",
            "crosses_per_90": 1.8 if pos == "W" else 0.4,
            "aerial_duel_win_pct": 0.58 if pos == "ST" else 0.48,
            "penalty_conversion_rate": 0.72,
            "yellow_per90": 0.3,
            "reds_season": 0,
            "late_foul_rate": 0.05,
            "suspension_cover": 0.7,
        })
    return squad
