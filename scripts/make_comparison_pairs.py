import json, itertools
from pathlib import Path
EXP = Path("/Users/nicolas/.codex/worktrees/4314/racer/experiments")
W = EXP/"2026-11-07-asset-mining/references/web"
M = EXP/"2026-11-07-comparison-matrix/output/matrix"
MC = Path("/Users/nicolas/Documents/github/reverse-engineering/games/racer/experiments/2026-11-05-city-scale/output/reference-images")
def w(p): return W/p
G = {
 "night": ([
  w("gran_turismo_4/gt4_hong_kong_neon_rx8.jpg"), w("gran_turismo_4/gt4_hong_kong_street_canyon.jpg"),
  w("midnight_club_3_dub_edition/mc3_corvette_night_street.jpg"), w("midnight_club_3_dub_edition/mc3_burning_rubber_night_lowrider.jpg"),
  w("juiced_2_hot_import_nights/j2_pc_teal_s15_night_circuit.jpg"), w("juiced_2_hot_import_nights/j2_pc_green_hatch_night_time_attack.jpg"),
  w("juiced_2_hot_import_nights/j2_ps3_big_ben_night_moon.jpg"), w("street_legal_racing_redline/slrr_night_street_start.jpg"),
  w("street_legal_racing_redline/slrr_night_headlights_turbo.jpg"), w("street_legal_racing_redline/slrr_night_moon_s14_rear.jpg"),
  w("street_legal_racing_redline/slrr_night_road_exhaust_flame.jpg"), w("project_gotham_racing_4/pgr4_shanghai_neon_street.png"),
  w("project_gotham_racing_4/pgr4_tokyo_night_lights.png"), w("grid/grid_night_city_rear_view.jpg"),
  w("need_for_speed_most_wanted_2012/nfsmw12_wet_street_police_roadblock.jpg"), MC/"mcla-07.jpg", MC/"mcla-10.jpg"],
  ["street-night-elevated","street-night-rear","street-night-front","street-night-left","street-night-right","neon-night-front","neon-night-left","closeup-night-rear","closeup-night-left"]),
 "dusk": ([
  w("midnight_club_los_angeles/mcla_datsun_mirror_view_sunset.jpg"), w("midnight_club_los_angeles/mcla_saleen_s7_closeup_dusk.jpg"),
  w("midnight_club_los_angeles/mcla_rx8_hollywood_sign.jpg"), w("juiced_2_hot_import_nights/j2_ps3_camo_bmw_dusk_colosseum.jpg"),
  w("street_legal_racing_redline/slrr_dusk_chase_view_trees.jpg"), w("grid/grid_cockpit_tokyo_sunset.jpg"),
  w("need_for_speed_most_wanted_2012/nfsmw12_bmw_m3_backlit_police_drift.jpg"), w("project_gotham_racing_4/pgr4_st_petersburg_church_bikes.png"),
  MC/"mcla-05.jpg", MC/"mcla-08.jpg"],
  ["street-dusk-rear","street-dusk-left","street-dusk-right","street-dusk-front","street-dusk-elevated","closeup-dusk-left","closeup-dusk-rear"]),
 "day": ([
  w("burnout_paradise/burnout_city_street_billboards_sun.jpg"), w("burnout_paradise/burnout_palm_street_crosswalk_cars.jpg"),
  w("gran_turismo_4/gt4_third_person_tree_lined_road.jpg"), w("gran_turismo_4/gt4_white_rx8_street_circuit.jpg"),
  w("midnight_club_los_angeles/mcla_lamborghini_convertible_crosswalk.jpg"), w("midnight_club_los_angeles/mcla_blue_sportbike_rider_daylight.jpg"),
  w("street_legal_racing_redline/slrr_red_sedan_street_daylight.jpg"), w("street_legal_racing_redline/slrr_red_coupe_road_highangle.jpg"),
  w("street_legal_racing_redline/slrr_mustang_stripes_track.jpg"), w("street_legal_racing_redline/slrr_fence_banked_curve.jpg"),
  w("juiced_2_hot_import_nights/j2_pc_olive_hatch_pale_circuit.jpg"), w("need_for_speed_most_wanted_2012/nfsmw12_gtr_airborne_skyline.jpg"),
  MC/"mcla-02.jpg", MC/"mcla-03.jpg", MC/"mcla-04.jpg", MC/"mcla-09.jpg"],
  ["street-day-rear","street-day-front","street-day-left","street-day-right","street-day-elevated","closeup-day-rear"]),
 "smoke": ([
  w("burnout_paradise/burnout_hotrod_wheelie_tyre_marks.jpg"), w("juiced_2_hot_import_nights/j2_pc_teal_s15_drift_session.jpg"),
  w("juiced_2_hot_import_nights/j2_ps3_orange_silvia_drift_grandstand.jpg"), w("juiced_2_hot_import_nights/j2_ps3_three_car_drift_arena.jpg"),
  w("street_legal_racing_redline/slrr_drift_smoke_topdown.jpg"), w("midnight_club_3_dub_edition/mc3_burning_rubber_night_lowrider.jpg"),
  MC/"mcla-06.jpg", w("need_for_speed_most_wanted_2012/nfsmw12_bmw_m3_backlit_police_drift.jpg")],
  ["brake-day-left","brake-day-rear","brake-night-rear","brake-night-left","launch-day-left"]),
 "motion": ([
  w("need_for_speed_most_wanted_2005/nfsmw05_highway_nitro_motion_blur.jpg"), MC/"mcla-01.jpg", MC/"mcla-11.jpg", MC/"mcla-12.jpg",
  w("forza_horizon/fh1_cockpit_race_start.png"), w("need_for_speed_most_wanted_2012/nfsmw12_gtr_airborne_skyline.jpg"),
  w("grid/grid_night_city_rear_view.jpg"), w("project_gotham_racing_4/pgr4_tokyo_night_lights.png")],
  ["speed-day-14s","speed-day-10s","speed-day-6s","speed-night-14s","speed-night-10s","speed-night-6s"]),
 "closeup": ([
  w("need_for_speed_most_wanted_2005/nfsmw05_bmw_m3_wheel_closeup_police.jpg"), w("gran_turismo_4/gt4_photo_mode_red_mazda_cx7.jpg"),
  w("gran_turismo_4/gt4_renault5_turbo_headlights.jpg"), w("midnight_club_los_angeles/mcla_saleen_s7_closeup_dusk.jpg"),
  w("street_legal_racing_redline/slrr_mustang_stripes_track.jpg"), w("gran_turismo_4/gt4_hood_view_stone_wall_hud.jpg")],
  ["paint-red-left","paint-blue-left","paint-black-left","closeup-day-left","closeup-night-left","closeup-dusk-rear"]),
 "garage": ([
  w("midnight_club_3_dub_edition/mc3_cadillac_cts_garage.jpg"), w("midnight_club_3_dub_edition/mc3_hummer_h1_garage.jpg"),
  w("midnight_club_3_dub_edition/mc3_impala_garage.jpg"), w("juiced_2_hot_import_nights/j2_ps3_silvia_indoor_circuit.jpg")],
  ["garage-ui","course-ui"]),
}
pairs=[]
for g,(refs,racers) in G.items():
    for r,rc in zip(refs, itertools.cycle(racers)):
        assert r.exists(), r
        pngs = M/(rc+".png"); assert pngs.exists(), pngs
        pairs.append({"group":g,"ref":str(r),"ref_label":Path(r).stem,"racer":str(pngs),"racer_label":"Racer "+rc})
out = Path("/Users/nicolas/.codex/worktrees/4314/racer/experiments/2026-11-07-comparison-matrix/pairs.json")
out.write_text(json.dumps(pairs,indent=1)); print(len(pairs),"pairs;",len({p['racer'] for p in pairs}),"distinct Racer frames;",len({p['ref'] for p in pairs}),"distinct refs")
