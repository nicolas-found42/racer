#!/usr/bin/env python3
"""Remove known decorative primitives from pinned adapted native Toyo templates only."""
import argparse,hashlib,json,os,shlex,shutil
from pathlib import Path
from prepare_gt4_vehicle import pack,unpack
from prepare_mcla_vehicle import read_regular
from vehicle_clearance import descriptor,require
from fit_vehicle_tracks import frames,positions
TEMPLATE_SHA='d1689b1bff3a0460e1171904c53f41f607693954dc645fded2a3587c7841ab69'
STRUCTURE=(('toyo_tyre',729,3840),('OZ_MICHELANGELO',2126,7584),('brake_disc',96,276),('BLACK2',162,480))
LABELS=('FL','FR','RL','RR')
def strip(raw,text,source_sha,descriptor_sha,template_sha):
 require(len(raw)<=16*1024**2 and hashlib.sha256(raw).hexdigest()==source_sha,'source_pin');require(len(text.encode())<=32768 and hashlib.sha256(text.encode()).hexdigest()==descriptor_sha,'descriptor_pin');require(template_sha==TEMPLATE_SHA,'template_pin');fields,wheels,roles=descriptor(text);require(fields['sha256']==[source_sha],'descriptor_join');doc,binary=unpack(raw)
 matches=[s for s in doc.get('extras',{}).get('sources',[])if s.get('bank')=='shared' and s.get('key')==641716538];require(len(matches)==1 and matches[0].get('sha256')==template_sha and matches[0].get('record',[None]*4)[3]==83602,'native_template_join');parents,world,owners=frames(doc,roles);before=positions(doc,binary,world);changes=[];found=set()
 for ni,node in enumerate(doc['nodes']):
  if not node.get('name','').startswith('ADAPTED_NATIVE_TOYO_TYRE_'):continue
  label=node['name'].removeprefix('ADAPTED_NATIVE_TOYO_TYRE_');require(label in LABELS and label not in found and roles.get(ni)==('wheel',LABELS.index(label)),'template_binding');found.add(label);require(sum(n.get('mesh')==node['mesh']for n in doc['nodes'])==1,'template_mesh_alias');mesh=doc['meshes'][node['mesh']];structure=[]
  for p in mesh['primitives']:
   require(p.get('mode',4)==4 and not p.get('targets') and 'material'in p,'template_primitive');structure.append((doc['materials'][p['material']]['name'],doc['accessors'][p['attributes']['POSITION']]['count'],doc['accessors'][p['indices']]['count']))
  require(tuple(structure)==STRUCTURE,'unknown_template_structure');removed=[{'material':name,'positions':pc,'expanded_indices':ic}for name,pc,ic in structure[1:]];mesh['primitives']=mesh['primitives'][:1];changes.append({'node':ni,'wheel':label,'kept_material':'toyo_tyre','removed':removed})
 require(found==set(LABELS),'four_templates_required');_,after_world,_=frames(doc,roles);after=positions(doc,binary,after_world);require(all(after[i]==before[i]for i in before if i not in {c['node']for c in changes}),'unrelated_geometry_changed')
 for c in changes:require(after[c['node']]==before[c['node']][:729],'rubber_positions_changed')
 receipt={'schema':1,'source_prepared_sha256':source_sha,'source_descriptor_sha256':descriptor_sha,'native_template_sha256':template_sha,'changes':changes,'binary_images_materials_accessors_unchanged':True,'non_template_nodes_transforms_primitives_unchanged':True,'geometry_descriptors_preserved_conservative':True,'runtime_player_eligible':False,'limits':['Racer-authored template primitive selection retains only toyo_tyre material; OZ wheelface, decorative disc and BLACK2 template primitives omitted. Canonical input remains unchanged.','No native TYRE_PROFILE generation or stock rim scaling consumer recovered. MX5 remains research HOLD.','All source BIN/images/material definitions/accessors are preserved; omitted decorative geometry remains in unused source buffer ranges.','Candidate requires fresh native loader, rendered wheel appearance and physics checks.']};doc.setdefault('extras',{})['racerTemplateRubberFilter']=receipt;result=pack(doc,binary);require(len(result)<=16*1024**2,'output_budget');digest=hashlib.sha256(result).hexdigest();rows=[shlex.split(s)for s in text.splitlines()if s.strip()];rows[1][1]='vehicle-'+digest;rows[3][1]=digest+'.glb';rows[4][1]=digest;newtext='\n'.join(' '.join(json.dumps(v)if row[0]in('id','name','mesh')and i==1 else v for i,v in enumerate(row))for row in rows)+'\n';receipt['prepared_sha256']=digest;return result,newtext,receipt

def publish(path,source_sha,descriptor_sha,template_sha,output):
 text=read_regular(path,32768).decode();raw=read_regular(path.with_suffix('.glb'),16*1024**2);result,newtext,receipt=strip(raw,text,source_sha,descriptor_sha,template_sha);require(not output.exists() and not any(p.is_symlink()for p in(output,*output.parents)),'fresh_output');require(shutil.disk_usage(output.parent).free>=20*1024**3,'disk_budget');output.mkdir(mode=0o700)
 for name,data in ((receipt['prepared_sha256']+'.glb',result),(receipt['prepared_sha256']+'.vehicle',newtext.encode()),('receipt.json',(json.dumps(receipt,indent=2)+'\n').encode())):
  with os.fdopen(os.open(output/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb')as f:f.write(data)
 return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('descriptor',type=Path);p.add_argument('--source-sha256',required=True);p.add_argument('--descriptor-sha256',required=True);p.add_argument('--template-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(publish(a.descriptor,a.source_sha256,a.descriptor_sha256,a.template_sha256,a.output),indent=2))
