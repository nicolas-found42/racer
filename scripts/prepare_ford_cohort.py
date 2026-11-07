#!/usr/bin/env python3
"""Pinned Ford cohort candidates with explicitly validated default material variants."""
import argparse,hashlib,json,os,shutil,copy
from pathlib import Path
from prepare_gt4_vehicle import unpack,pack,require
from prepare_ford_vehicle import prepare,source_physics
from ford_cohort_registry import PROFILES
PINS={'FOCUS_SVT':'b694708fefefa9cb85b9c8125ade226a973e9f0a87d1b05298eae3d49ffbc844','F150':'1cd44268e1a9aebfc33e810a7556044ef6c2d18e9eb00bf22413abadbb3a0d04'}
CONFIG_PINS={'FOCUS_SVT': {'cardata.txt': 'cb0d876944ffaa966b64f1d434a3ae0970d03452b155f00e854248ab0ea4a510', 'tyres_front.txt': '9060c4480851fb9c67bbbe94f62761a0397036f51fce253b91931d1065c5d12f', 'tyres_back.txt': '289f5e9791d153a8479e876d8a79ac3c8202935e184c1b2aba85671e4e4d5d2c'}, 'F150': {'cardata.txt': '0fb79aceb8d7c43b117f68e737a9a388055a508e884504be3370e4fe0d04b3da', 'tyres_front.txt': 'e97950ae898642bd8598ffdf601fa8f258096faeb0657f35f01c94204881379a', 'tyres_back.txt': 'a36673ccfc1badc4a61094ca5f1d94c6c99c8c83967a02c9417badaa977d51ac'}}
NAMES={'FOCUS_SVT':'Ford SVT Focus 2002 (source candidate)','F150':'Ford F-150 2001 (source candidate)'}
SUPPORTED_CODES=tuple(code for code,p in PROFILES.items() if p['approval_occurrences']==['1'])
def profile(code,*,research_any_approval=False):
 require(type(research_any_approval)is bool,'research_mode')
 require(code in PROFILES and (research_any_approval or PROFILES[code]['approval_occurrences']==['1']),'source_approval_unknown')
 p=PROFILES[code]
 return {'source_sha256':PINS.get(code,p['source_sha256']), 'config_pins':CONFIG_PINS.get(code,p['config_pins']),
         'name':NAMES.get(code,'Ford '+p['name']+' '+str(p['year'])+' (source candidate)'), 'native_sha256':p['native']['sha256'], 'physics_sha256':p['physics_sha256']}
sha=lambda b:hashlib.sha256(b).hexdigest()
SUFFIXES=('FRONT_LEFT','FRONT_RIGHT','BACK_LEFT','BACK_RIGHT')
def normalize_assembly(d):
 """Expose source HUB geometry as carriers; wheel-static children inherit named owner."""
 scenes=[s for s in d['scenes']if s.get('extras',{}).get('sourceTree')==0 and s.get('extras',{}).get('visibilityPreset')=='low_speed'];require(len(scenes)==1 and len(scenes[0]['nodes'])==1,'low_speed_scene');root=scenes[0]['nodes'][0];require(len(d['nodes'])<=4091,'normalization_node_budget');rn=d['nodes'][root];require(rn.get('translation',[0,0,0])==[0,0,0]and rn.get('scale',[1,1,1])==[1,1,1]and not any(k in rn for k in('matrix','rotation')),'normalization_root_frame');carriers={};aliases=[];seen=set();hub_owners=set()
 def walk(index,scale,translation,owner,depth=0):
  require(depth<62,'normalization_depth')
  require(index not in seen and len(seen)<4090,'normalization_graph');seen.add(index);n=d['nodes'][index];require(not any(k in n for k in('matrix','rotation')),'source_rotation');ns=n.get('scale',[1,1,1]);nt=n.get('translation',[0,0,0]);worlds=[scale[k]*ns[k]for k in range(3)];worldt=[translation[k]+scale[k]*nt[k]for k in range(3)];names=n.get('extras',{}).get('sourceNames',[]);hubs=[i for i,s in enumerate(SUFFIXES)if'HUB_'+s in names]
  if hubs:
   require(len(hubs)==1 and owner is None and hubs[0]not in hub_owners,'hub_owner');owner=hubs[0];hub_owners.add(owner)
   if 'mesh'in n:
    clone=copy.deepcopy(n);clone.pop('children',None);clone['name']='Racer source HUB carrier '+SUFFIXES[owner];clone['translation']=worldt;clone['scale']=worlds;clone['extras']['originalSourceNames']=names[:];clone['extras']['sourceNames']=[];clone['extras']['racerCarrierSourceNode']=index;ci=len(d['nodes']);d['nodes'].append(clone);carriers[ci]=owner;n.pop('mesh')
  if owner is not None and 'mesh'in n and 'WHEEL_STATIC'in names:
   require(not any(x.startswith('WHEEL_')and x!='WHEEL_STATIC'for x in names),'static_owner_ambiguity');n['extras']['originalSourceNames']=names[:];n['extras']['sourceNames']=[*names,'WHEEL_'+SUFFIXES[owner]];aliases.append({'node':index,'source_names':names,'inherited_source_hub_owner':SUFFIXES[owner]})
  for child in n.get('children',[])[:]:walk(child,worlds,worldt,owner,depth+1)
 walk(root,[1,1,1],[0,0,0],None);require(hub_owners==set(range(4)),'four_source_hubs');d['nodes'][root]['children'].extend(carriers);return {'carrier_nodes':carriers,'static_wheel_owner_aliases':aliases,'rule':'Named source HUB mesh preserves its source world frame as steering carrier; WHEEL_STATIC descendant inherits exact named source hub ownership.'}
def default_variants(document):
 variants=document.get('extensions',{}).get('KHR_materials_variants',{}).get('variants',[]);require(isinstance(variants,list)and len(variants)<=64,'variant_budget');removed=[]
 for mi,mesh in enumerate(document['meshes']):
  for pi,p in enumerate(mesh['primitives']):
   extensions=p.get('extensions',{})
   if not extensions:continue
   require(set(extensions)=={'KHR_materials_variants'},'unsupported_primitive_extension');mappings=extensions['KHR_materials_variants'].get('mappings');require(isinstance(mappings,list)and 0<len(mappings)<=64,'variant_mappings');seen=set();default=[]
   for row in mappings:
    material=row.get('material');ids=row.get('variants');require(type(material)is int and 0<=material<len(document['materials'])and isinstance(ids,list)and ids,'variant_material')
    for i in ids:
     require(type(i)is int and 0<=i<len(variants)and i not in seen,'variant_index');seen.add(i)
     if i==0:default.append(material)
   require(default==[p.get('material')],'variant_default');removed.append({'mesh':mi,'primitive':pi,'mappings':mappings});p.pop('extensions')
 return {'selected_variant_index':0,'source_variant_names':[v.get('name')for v in variants],'removed_primitive_mappings':removed,'rule':'Preserve source default primitive material and all material/image/BIN bytes; optional alternate variant selection not represented by Racer.'}
def prepare_candidate(data,code,physics,*,research_any_approval=False,static_suspension_rest=False):
 require(type(static_suspension_rest)is bool,'static_suspension_mode')
 contract=profile(code,research_any_approval=research_any_approval);require(isinstance(physics,dict) and {r['file']:r['sha256']for r in physics.get('files',[])}==contract['config_pins'],'config_pin');require(sha(json.dumps(physics,sort_keys=True,separators=(',',':')).encode())==contract['physics_sha256'],'config_semantics_pin');require(len(data)<=16*1024**2 and sha(data)==contract['source_sha256'],'source_pin');d,b=unpack(data);require(d.get('extras',{}).get('originalModelSha256')==contract['native_sha256'],'native_model_pin');original_binary=bytes(b);variant=default_variants(d);rest_policy=None
 if static_suspension_rest:
  from ford_static_rest import normalize
  rest_policy=normalize(d,code,sha(data))
 assembly=normalize_assembly(d);normalized=pack(d,b);name=contract['name'].replace(' (source candidate)',' (static suspension rest candidate)')if static_suspension_rest else contract['name'];raw,desc,receipt=prepare(normalized,'ford-racing-2/'+code,name,physics);out,bb=unpack(raw);require(bytes(bb)==original_binary,'binary_regression')
 policy={'schema':1,'source_sha256':sha(data),'normalization_sha256':sha(normalized),'runtime_player_eligible':False,'variant_default_policy':variant,'assembly_normalization':assembly,'authority':'Pinned native-source-derived static assembly and configured tyre radii; explicit Racer conversion, not original runtime parity','limits':['Source-only candidate; runtime/GPU/physics/factory size acceptance pending.','Source metadata approval is a declaration, not proof of selectable original runtime roster.','Default livery only; alternate source variant mappings retained in provenance but not dynamically selected.']};
 if rest_policy:policy['static_suspension_rest']=rest_policy
 if research_any_approval:policy['research_approval_policy']={'source_approval_occurrences':PROFILES[code]['approval_occurrences'],'native_roster':'unknown','runtime_player_eligible':False,'authority':'Explicit research mode; source approval0/conflict is not a user exclusion or automatic player eligibility.'}
 out['extras']['racerFordCohort']=policy;prepared=pack(out,bb);digest=sha(prepared);old=receipt['prepared_sha256'];desc=desc.replace(old,digest).replace(receipt['source_sha256'],sha(data));lines=desc.splitlines();lines[0]='RACER_VEHICLE 2';bindings=[]
 for i,line in enumerate(lines):
  if not line.startswith('group '):continue
  _,node,wheel=line.split();node=int(node);wheel=int(wheel);role='carrier '+('FL','FR','RL','RR')[assembly['carrier_nodes'][node]]if node in assembly['carrier_nodes']else('body'if wheel<0 else'wheel '+('FL','FR','RL','RR')[wheel]);lines[i]='group '+str(node)+' '+role;bindings.append({'node':node,'role':role})
 if static_suspension_rest:
  from ford_static_rest import contain_roles
  contain_roles(out,bb,bindings,receipt['wheels'])
 desc='\n'.join(lines)+'\n';receipt.update(source_sha256=sha(data),source_bytes=len(data),prepared_sha256=digest,prepared_bytes=len(prepared),cohort=policy,binding_roles=bindings);return prepared,desc,receipt

def publish(source,code,config,output,*,research_any_approval=False,static_suspension_rest=False):
 require(not source.is_symlink()and source.is_file()and source.stat().st_size<=16*1024**2,'source_file');data=source.read_bytes();physics=source_physics(config,'ford-racing-2/'+code);card_bytes=(config/'cardata.txt').read_bytes();require(sha(card_bytes)==profile(code,research_any_approval=research_any_approval)['config_pins']['cardata.txt'],'cardata_pin');card=card_bytes.decode();active=[x.split('//')[0].split()for x in card.splitlines()];approved=[x[1]for x in active if len(x)==2 and x[0]==':CAR_APPROVED'];require(approved==PROFILES[code]['approval_occurrences']and(research_any_approval or approved==['1']),'source_not_approved');raw,desc,r=prepare_candidate(data,code,physics,research_any_approval=research_any_approval,static_suspension_rest=static_suspension_rest);require(not output.exists()and not any(p.is_symlink()for p in(output,*output.parents)),'fresh_output');require(shutil.disk_usage(output.parent).free>=20*1024**3,'free_space');output.mkdir(mode=0o700)
 for suffix,payload in [('.glb',raw),('.vehicle',desc.encode()),('.json',(json.dumps(r,indent=2)+'\n').encode())]:
  fd=os.open(output/(r['prepared_sha256']+suffix),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb')as f:f.write(payload)
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--code',choices=tuple(PROFILES),required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--research-any-approval',action='store_true',help='Research only: preserve approval0/conflict as unknown native roster; never grants player eligibility.');p.add_argument('--static-suspension-rest',action='store_true',help='Exact EX/INDIGO research lane: preserve suspension source rest geometry as body-fixed drawables; no native animation claim.');a=p.parse_args();print(json.dumps(publish(a.source,a.code,a.config,a.output,research_any_approval=a.research_any_approval,static_suspension_rest=a.static_suspension_rest),indent=2))
