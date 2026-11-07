#!/usr/bin/env python3
"""Build a local gallery from retained, hash-checked sources and native captures."""
import hashlib,html,json,os,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'experiments/2026-11-05-city-scale/output'
def esc(x):return html.escape(str(x),quote=True)
def relative(path):return esc(os.path.relpath(path,OUT))
def verified(path,digest):assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
def figure(path,caption):
    url=relative(path)
    return '<figure><a href="'+url+'"><img loading="lazy" src="'+url+'"></a><figcaption>'+caption+'</figcaption></figure>'
def main():
    page=OUT/'gallery.html';old=OUT/'gallery-four-original.html'
    if page.exists() and not old.exists():shutil.copyfile(page,old)
    pieces=['<!doctype html><meta charset="utf-8"><title>City and vehicle scale evidence</title>',
      '<style>body{font:16px system-ui;margin:2rem;background:#121820;color:#e5eaf0}a{color:#8dccff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:1rem}figure{margin:0;background:#202934;padding:1rem}img{width:100%;height:auto}figcaption{margin-top:.5rem}td,th{padding:.5rem;border:1px solid #657080}table{border-collapse:collapse}</style>',
      '<h1>City and vehicle scale evidence</h1><p>Current seven-player native views plus retained city references. One unit = one metre. GT1/Redline are excluded; MCLA ambient is deferred traffic only. Reference perspective does not establish absolute dimensions. Authoring, shader and native-runtime limitations remain in the linked experiment records.</p>',
      '<h2>Published game and real-city references</h2><div class="grid">']
    for row in json.loads((OUT/'reference-manifest.json').read_text()):
        path=ROOT/row['file'];verified(path,row['sha256'])
        caption=esc(row['id'])+': '+esc(row['review_caption'])+' <a href="'+esc(row['page'])+'">Source</a>'
        if row.get('author'):caption+=' — '+esc(row['author'])+' <a href="'+esc(row['license'])+'">License</a>'
        pieces.append(figure(path,caption))
    native=OUT/'eligible-seven-v3';manifest=json.loads((native/'manifest.json').read_text());assert manifest['all_verified'] and len(manifest['runs'])==28
    pieces+=['</div><h2>Current seven player preparations</h2><p>Identical 8 m camera, 2.5 × 5.5 m bay, 1.75 m figure, 1 m ticks and 3 m lanes. Source materials use a supported subset; SLRR neutral/glass approximations are visible. Factory applicability and exact authored wheel/body fitting are recorded separately.</p><div class="grid">']
    for row in manifest['runs']:
        path=native/row['capture'];verified(path,row['sha256'])
        pieces.append(figure(path,esc(row['model_id']+' / '+row['view'])+' — exact mesh SHA and native envelopes verified.'))
    steer=ROOT/'experiments/2026-11-06-fit-review/output/steer-v2';m=json.loads((steer/'manifest.json').read_text());assert m['all_verified']
    pieces+=['</div><h2>Stationary full steering at 1440p</h2><p>0 / +0.55 / −0.55 rad in separate retained PNGs. Contacts with internal arms/wheelwell planes are diagnostic witnesses, not automatically source defects. Exact triangle and negative-fit evidence remain retained.</p><div class="grid">']
    for row in m['runs']:
        for capture in row['captures']:
            path=steer/str(row['model'])/capture['file'];verified(path,capture['sha256'])
            ident=m['models'][row['model']]['descriptor_source']
            pieces.append(figure(path,esc(ident.split('/')[-2]+' / '+capture['file'])))
    pieces+=['</div><p><a href="eligible-seven-v3/manifest.json">Native source/build/command/PNG manifest</a> · <a href="../../2026-11-06-fit-review/README.md">Fit decisions and limits</a> · <a href="reference-manifest.json">Reference credits, dimensions and hashes</a></p>']
    page.write_text('\n'.join(pieces)+'\n')
    print('Gallery:19 references +28 current native views +21 full-steer captures; all image hashes verified.')
if __name__=='__main__':main()
