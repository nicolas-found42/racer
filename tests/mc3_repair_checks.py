#!/usr/bin/env python3
"""Exact-name archive join regressions and actual repaired geometry acceptance."""
import sys,json,hashlib,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from repair_mc3_vehicle import archive,packed_name,frames,repair,CHARS
from prepare_gt4_vehicle import unpack,PreparationError

def encode(name):
 symbols=[CHARS.index(c)for c in name]+[0];symbols+=[0]*(-len(symbols)%4);return b''.join(sum(symbols[i+j]<<(j*6)for j in range(4)).to_bytes(3,'little')for i in range(0,len(symbols),4))
def main():
 assert packed_name(encode('hood.mesh'),0,'')=='hood.mesh'
 try:packed_name(b'\xff\xff',0,'');raise AssertionError('bad name accepted')
 except PreparationError:pass
 b=[{'rotation_raw':[0,0,0],'local_position':[1,2,3],'parent':None},{'rotation_raw':[0,0,0],'local_position':[2,3,4],'parent':0}];assert frames(b)[1][0]==[3,5,7]
 print('PASS known-answer six-bit filename decode, truncated name rejection, affine ancestry')
 if len(sys.argv)<2:return
 out=Path(sys.argv[1]);root=out.parent.parent;receipt=json.loads((out/'receipt.json').read_text());dat=root/'vp_corvettez06_03.dat';rows=archive(dat.read_bytes());manifest=json.loads((out.parent/'source-manifest.json').read_text());assert len(rows)==9
 rawdoc,rawbin=unpack((out/'stock-complete-source.glb').read_bytes());origdoc,origbin=unpack((root/'assets/objects/b0e50f8c609b770ece74ea511312a11e7b79f6e6fff6331da7ff249ba6328806.glb').read_bytes());assert rawbin[:len(origbin)]==origbin
 for k in ['nodes','meshes','accessors','bufferViews']:
  assert rawdoc[k][:len(origdoc[k])]==origdoc[k]
 assert rawdoc['materials']==origdoc['materials'] and rawdoc['images']==origdoc['images']
 joins=receipt['external_repair']['joins'];assert len(joins)==7 and len({x['part'].casefold()for x in joins})==7
 for x in joins:
  r=x['member'];native=next(v for v in rows if v['ordinal']==r['ordinal']);assert native==r and Path(r['name']).name.casefold()==(x['part']+'.pck').casefold();assert hashlib.sha256((out/(str(r['ordinal'])+'.pck')).read_bytes()).hexdigest()==r['sha256']
 assert any(x['part']=='vroot_hd_hd_h.mesh' and x['bone']==19 for x in joins)
 sys.path.insert(0,str(Path(__file__).parent));from ford_vehicle_checks import containment
 glb=(out/(receipt['prepared_sha256']+'.glb')).read_bytes();containment(glb,receipt);assert hashlib.sha256(glb).hexdigest()==receipt['prepared_sha256'];assert abs(receipt['wheelbase']-2.8043999671936035)<1e-6
 with tempfile.TemporaryDirectory()as temp:
  bad=json.loads(json.dumps(manifest));bad['members'][2]['source']['name']='wrong.mesh.pck';p=Path(temp)/'bad.json';p.write_text(json.dumps(bad));dest=Path(temp).resolve()/'rejected'
  try:repair(dat,root/'assets/objects/b0e50f8c609b770ece74ea511312a11e7b79f6e6fff6331da7ff249ba6328806.glb',p,root/'reference-mc3_pck.py',dest);raise AssertionError('bad filename association accepted')
  except PreparationError:pass
  assert not dest.exists()
 print('PASS all7 exact native filenames/hash joins, hood bone19, old geometry/materials preserved, actual containment, no-rescale wheelbase, mutated manifest rejection')
if __name__=='__main__':main()
