"""Assemble references/j2 from downloaded originals (bytes copied unaltered), verify with PIL, write manifest.json.
usage: j2_refs_build.py <download_scratch_dir> <out_dir>"""
import hashlib, json, shutil, sys
from pathlib import Path
from PIL import Image
W, OUT = Path(sys.argv[1]), Path(sys.argv[2])
S = 'https://cdn.sanity.io/images/vlhyuihz/production/'
GH = 'https://raw.githubusercontent.com/anishchandra24/Juiced2-Recompiled/main/docs/screenshots/'
GSA = 'https://www.gamespot.com/a/uploads/original/gamespot/images/2007/170/reviews/'
GSW = 'https://www.gamespot.com/wp-content/uploads/original/gamespot/images/2007/'
# (local path under W, slug, element, platform/notes, source page, url)
SPEC = [
 ('gh/01-titlescreen.png','title_screen','Title screen (logo, press-start layout)','Xbox 360 build rendered 1080p via fan static recompilation (Juiced2-Recompiled README)','https://github.com/anishchandra24/Juiced2-Recompiled',GH+'01-titlescreen.png'),
 ('gh/02-mainmenu.png','main_menu_career_beam','Main menu: selection beam, icon medallion, A/B prompts','Xbox 360 build via recompilation, 1080p','https://github.com/anishchandra24/Juiced2-Recompiled',GH+'02-mainmenu.png'),
 ('gh/03-ingame.png','hud_drift_event_score_arcs','Drift-event HUD: HIN TV score/target plate, arc meters, gear+mph, lap, floating score','Xbox 360 build via recompilation, 1080p','https://github.com/anishchandra24/Juiced2-Recompiled',GH+'03-ingame.png'),
 ('gh/04-ingame.png','goal_completed_popup','Goal-completed popup: stamp, framed icon, caption, A prompt, HIN TV banner','Xbox 360 build via recompilation, 1080p','https://github.com/anishchandra24/Juiced2-Recompiled',GH+'04-ingame.png'),
 ('gh/05-garage.png','career_menu_club_carousel','Career hub: title+cash top-left, icon carousel bottom-centre, 3 button prompts','Xbox 360 build via recompilation, 1080p','https://github.com/anishchandra24/Juiced2-Recompiled',GH+'05-garage.png'),
 ('moby/339425_race_results.jpg','results_race_results','Race / challenge results panel (score target vs achieved)','Windows, Russian locale (MobyGames user screenshot)','https://mobygames.com/game/36785/juiced-2-hot-import-nights/screenshots/windows/339425','https://cdn.mobygames.com/screenshots/11154659-juiced-2-hot-import-nights-windows-race-results.jpg'),
 ('moby/339428_tuning.jpg','tuning_class_matrix','Tuning screen: performance class matrix with locks','Windows, Russian locale (MobyGames user screenshot)','https://mobygames.com/game/36785/juiced-2-hot-import-nights/screenshots/windows/339428','https://cdn.mobygames.com/screenshots/11153400-juiced-2-hot-import-nights-windows-tuning-screen-some-kits-are-l.jpg'),
 ('moby/339430_career_menu.jpg','career_menu_garage_carousel','Career menu / garage carousel with car and driver','Windows, Russian locale (MobyGames user screenshot)','https://mobygames.com/game/36785/juiced-2-hot-import-nights/screenshots/windows/339430','https://cdn.mobygames.com/screenshots/11154641-juiced-2-hot-import-nights-windows-career-mode-main-menu.jpg'),
 ('moby/339435_choose_race.jpg','event_select_billboard','Event / race select billboard (course, prize money, laps, drivers)','Windows, Russian locale (MobyGames user screenshot)','https://mobygames.com/game/36785/juiced-2-hot-import-nights/screenshots/windows/339435','https://cdn.mobygames.com/screenshots/11154179-juiced-2-hot-import-nights-windows-you-can-choose-the-race.jpg'),
 ('gs/20070619_938449_002.jpg','garage_lift_parts_view','Garage lift / parts-install exploded view','Xbox 360 pre-release (GameSpot hands-on 2007-07-03)','https://www.gamespot.com/articles/juiced-2-hot-import-nights-hands-on/1100-6172858/',GSA+'802299-938449_20070619_002.jpg'),
 ('gs/821334-938452_20070906_001.jpg','hud_race_laps_pos_dial_map','Circuit race HUD: laps top-left, position top-right, map disc bottom-left, rev dial bottom-right','PS2 (GameSpot review gallery id 938452)','https://www.gamespot.com/reviews/juiced-2-hot-import-nights-review/1900-6179866/',GSW+'248/821334-938452_20070906_001.jpg'),
 ('gs/821335-938452_20070906_002.jpg','hud_drift_score_leaderboard','Drift HUD: HIN score plate + timer top-left, live leaderboard top-right, map + dial bottom','PS2 (GameSpot review gallery)','https://www.gamespot.com/reviews/juiced-2-hot-import-nights-review/1900-6179866/',GSW+'248/821335-938452_20070906_002.jpg'),
 ('gs/821336-938452_20070906_003.jpg','hud_drift_score_leaderboard_2','Drift HUD variant with red tail-light glow, score 114,761','PS2 (GameSpot review gallery)','https://www.gamespot.com/reviews/juiced-2-hot-import-nights-review/1900-6179866/',GSW+'248/821336-938452_20070906_003.jpg'),
 ('cand/02_ps2home.img','hud_race_laps_pos_dial','Circuit race HUD close to Xbox layout (1/5 LAPS, 1/6 POS, map disc, dial)','PS2 (ps2home.co.uk gallery)','https://ps2home.co.uk/juiced-2-hot-import-nights',S+'4caad72e3c71169ef07cd8cc2e790653dc03b65c-640x480.jpg'),
 ('cand/03_ps2home.img','hud_drift_score_plate','Drift HUD with score plate and 3-name leaderboard','PS2 (ps2home.co.uk gallery)','https://ps2home.co.uk/juiced-2-hot-import-nights',S+'493cde03eacb5d92dd6763944b118a1e322213d3-640x480.jpg'),
 ('cand/04_ps2home.img','hud_drift_score_plate_2','Drift HUD, second sample (00:57.19 timer, 114,761)','PS2 (ps2home.co.uk gallery)','https://ps2home.co.uk/juiced-2-hot-import-nights',S+'948c3dee0846889aacdc3e5b34ba19c5d71a41e2-640x480.jpg'),
 ('cand/08_ps2home.img','replay_prompt_continue_next_restart','Post-race replay: R badge top-left, CONTINUE / VIEW NEXT CAR / RESTART RACE footer','PS2 (ps2home.co.uk gallery)','https://ps2home.co.uk/juiced-2-hot-import-nights',S+'0495b6266edd12ffdf19585b7ad185117014fcc1-640x475.jpg'),
 ('cand/09_ps2home.img','replay_prompt_continue_next_restart_2','Replay overlay with pack of cars (second sample)','PS2 (ps2home.co.uk gallery)','https://ps2home.co.uk/juiced-2-hot-import-nights',S+'c752d3442ad903c494b6d9f63c995eabb76e40d2-640x475.jpg'),
 ('cand/12_ps2home.img','hud_race_laps_pos_dial_2','Circuit race HUD in snow (1/5 laps, 5/6 pos, map disc, rev dial 121 mph)','PS2 (ps2home.co.uk gallery)','https://ps2home.co.uk/juiced-2-hot-import-nights',S+'fcd6940043bd583bef1731c1dca16261b842db9f-640x480.jpg'),
 ('cand/13_ps2home.img','hud_race_laps_pos_dial_3','Circuit race HUD, BMW (2/6 pos, 158 mph)','PS2 (ps2home.co.uk gallery)','https://ps2home.co.uk/juiced-2-hot-import-nights',S+'d8220f25933a37ea2e4e89d70122b76dfcea3751-640x480.jpg'),
 ('cand/14_ps2home.img','hud_race_laps_pos_dial_4','Circuit race HUD with motion blur at high speed (6/6 pos, 74 mph)','PS2 (ps2home.co.uk gallery)','https://ps2home.co.uk/juiced-2-hot-import-nights',S+'edb64258e4635b215f958dd35e867ed4bd28f1b0-640x480.jpg'),
 ('ign/juiced-2-hot-import-nights-20070513060244444.jpg','garage_parts_shop_items_price','Garage parts view: ITEMS count and price top-right, doors/hood open','Xbox 360 preview (IGN AU hands-on 2007-05-13), 480px thumbnail','https://www.ign.com/articles/2007/05/13/juiced-2-hot-import-nights-au-hands-on','https://xbox360media.ign.com/xbox360/image/article/786/786298/juiced-2-hot-import-nights-20070513060244444.jpg'),
 ('cand/52_motoiq-ign.img','dna_celebrity_select_menu','Select-celebrity-driver menu: DNA helix icon, portrait, list, Xbox button footer','Xbox 360 (IGN image on motoiq.com article)','https://motoiq.com/need-for-speed-pro-street-juiced-2-hin','https://carsmedia.ign.com/cars/image/article/822/822067/the-celebrity-drivers-of-juiced-2-hot-import-nights-part-one-20070921113510963.jpg'),
 ('cand/18_vgchartz.img','garage_turntable_showroom','Showroom turntable ring (no HUD) used behind garage UI','Xbox 360 (vgchartz gallery)','https://www.vgchartz.com/game/6983/juiced-2-hot-import-nights/screenshots','https://www.vgchartz.com/games/pics/3508318aaa.jpg'),
 ('cand/22_vgchartz.img','garage_turntable_showroom_2','Showroom turntable ring, second car','Xbox 360 (vgchartz gallery)','https://www.vgchartz.com/game/6983/juiced-2-hot-import-nights/screenshots','https://www.vgchartz.com/games/pics/5704262aaa.jpg'),
]
man = []
for i, (src, slug, element, plat, page, url) in enumerate(SPEC, 1):
    p = W / src
    try:
        with Image.open(p) as im:
            im.load(); fmt = im.format; size = im.size
    except Exception as e:
        print('FAILED verify', src, e); continue
    ext = {'JPEG': 'jpg', 'PNG': 'png'}[fmt]
    name = 'j2_%02d_%s.%s' % (i, slug, ext)
    shutil.copyfile(p, OUT / name)
    man.append(dict(file=name, element=element, platform_notes=plat, source_page=page, source_url=url,
                    sha256=hashlib.sha256(p.read_bytes()).hexdigest(), width=size[0], height=size[1], format=fmt,
                    bytes=p.stat().st_size))
(OUT / 'manifest.json').write_text(json.dumps(man, indent=1))
print(len(man), 'images', sum(m['bytes'] for m in man) // 1024, 'KiB')
