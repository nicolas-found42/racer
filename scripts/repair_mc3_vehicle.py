#!/usr/bin/env python3
"""Repair exact seven MC3 Corvette stock joins; never infer names from member order."""
import argparse,copy,hashlib,importlib.util,json,math,struct,shutil
from pathlib import Path
from prepare_gt4_vehicle import require,unpack,pack
from prepare_source_vehicle import prepare
SHA='90b26498770a4f2e4bedf1480a8bcdbc6c8c8b26533088677ffbb4a8c020a26e'
CHARS='\x00 #$()-./?0123456789_abcdefghijklmnopqrstuvwxyz~\x7f'
sha=lambda b:hashlib.sha256(b).hexdigest()
def packed_name(data,offset,previous):
 symbols=[]
 while len(symbols)<340:
  require(offset+3<=len(data),'name_extent');word=int.from_bytes(data[offset:offset+3],'little');offset+=3;symbols.extend((word>>(6*i))&63 for i in range(4))
  if 0 in symbols:break
 require(0 in symbols,'name_termination');name=''
 if symbols[0]>=56:
  prefix=(symbols[1]-32)*8+symbols[0]-56;require(0<=prefix<=len(previous),'name_prefix');name=previous[:prefix];symbols=symbols[2:]
 for s in symbols:
  if s==0:return name
  require(s<len(CHARS),'name_symbol');name+=CHARS[s]
 raise ValueError('unterminated_name')
def archive(data):
 require(len(data)<=16*1024**2,'archive_budget');magic,n,info,names=struct.unpack_from('<4sIII',data);require(magic==b'Dave' and 0<n<=4096 and info>=n*16 and info%2048==0 and names%2048==0 and 2048+info+names<=len(data),'archive_header');block=data[2048+info:2048+info+names];previous='';out=[]
 for i in range(n):
  no,o,size,stored=struct.unpack_from('<4I',data,2048+i*16);name=packed_name(block,no,previous);previous=name;require(name and '..'not in name.split('/') and not name.startswith('/') and o>=2048+info+names and o+stored<=len(data) and size==stored,'archive_record');out.append({'ordinal':i,'name':name,'offset':o,'size':size,'stored':stored,'sha256':sha(data[o:o+size])})
 return out

def product(a,b):
 x,y,z,w=a;X,Y,Z,W=b;return[w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z]
def rotate(q,p):
 x,y,z,w=q;px,py,pz=p;tx,ty,tz=2*(y*pz-z*py),2*(z*px-x*pz),2*(x*py-y*px);return[px+w*tx+y*tz-z*ty,py+w*ty+z*tx-x*tz,pz+w*tz+x*ty-y*tx]
def frames(bones):
 result={};active=set()
 def f(i):
  require(type(i)is int and 0<=i<len(bones) and i not in active,'bone_graph')
  if i in result:return result[i]
  active.add(i);b=bones[i];sx,sy,sz=[math.sin(x/2)for x in b['rotation_raw']];cx,cy,cz=[math.cos(x/2)for x in b['rotation_raw']];q=[sx*cy*cz-cx*sy*sz,cx*sy*cz+sx*cy*sz,cx*cy*sz-sx*sy*cz,cx*cy*cz+sx*sy*sz];t=list(b['local_position'])
  if b['parent']is not None:
   T,Q=f(b['parent']);t=[a+c for a,c in zip(rotate(Q,t),T)];q=product(Q,q)
  active.remove(i);result[i]=(t,q);return result[i]
 return[f(i)for i in range(len(bones))]

def repair(dat,glb,manifest,reader,output):
 require(all(p.is_file() and not p.is_symlink()for p in [dat,glb,manifest,reader]),'regular_inputs')
 require(dat.stat().st_size<=16*1024**2 and glb.stat().st_size<=16*1024**2 and manifest.stat().st_size<=1024**2 and reader.stat().st_size<=1024**2,'input_budgets')
 require(sha(reader.read_bytes())=='68c6d61162563023560c4c71cf40bc729e2279918d8c9ef9e433df32de7bebde','reader_identity')
 require(sha(glb.read_bytes())=='b0e50f8c609b770ece74ea511312a11e7b79f6e6fff6331da7ff249ba6328806','source_glb_identity')
 require(shutil.disk_usage(output.parent).free>=20*1024**3,'disk_budget')
 require(not output.exists() and not output.is_symlink() and not any(p.is_symlink()for p in output.parents),'output_exists');data=dat.read_bytes();require(sha(data)==SHA,'dat_identity');records=archive(data);m=json.loads(manifest.read_text());require(m['carrier']['sha256']==SHA,'manifest_identity');byname={}
 for r in records:
  require(r['name']not in byname,'duplicate_member');byname[r['name']]=r
  ms=[v for v in m['members']if v['source']['ordinal']==r['ordinal']];require(len(ms)==1 and ms[0]['sha256']==r['sha256'] and ms[0]['source']['name']==r['name'] and ms[0]['source']['offset']==r['offset'],'manifest_native_join')
 output.mkdir(mode=0o700);spec=importlib.util.spec_from_file_location('mc3_native_pck',reader);native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
 main=[r for r in records if Path(r['name']).name=='vp_corvettez06_03.pck'];require(len(main)==1,'main_join');r=main[0];pckpath=output/'main.pck';pckpath.write_bytes(data[r['offset']:r['offset']+r['size']]);vehicle=native.read_vehicle(pckpath);rest=frames(vehicle['skeleton']['bones']);d,b=unpack(glb.read_bytes());require(d['extras']['car']=='vp_corvettez06_03' and len(d['nodes'])<4089,'source_glb');joins=[];newnodes=[];indices_total=0
 def add(values,typ,fmt,component):
  b.extend(b'\0'*(-len(b)%4));start=len(b)
  for v in values:b.extend(struct.pack('<'+fmt,*v))
  require(len(b)<=32*1024**2,'binary_budget');d['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(b)-start});a={'bufferView':len(d['bufferViews'])-1,'componentType':component,'count':len(values),'type':typ}
  if typ=='VEC3':a.update(min=[min(v[k]for v in values)for k in range(3)],max=[max(v[k]for v in values)for k in range(3)])
  d['accessors'].append(a);return len(d['accessors'])-1
 for part in vehicle['lods']['high']:
  if part['mesh']is not None:continue
  candidates=[r for name,r in byname.items()if Path(name).name.casefold()==(part['name']+'.pck').casefold()];require(len(candidates)==1,'external_name_join');r=candidates[0];raw=data[r['offset']:r['offset']+r['size']];path=output/(str(r['ordinal'])+'.pck');path.write_bytes(raw);me=native.read_mesh(path);primitives=[]
  for draw in me['draws']:
   mi=draw['material'];require(0<=mi<len(d['materials']) and d['materials'][mi]['extras']['index']==mi,'material_join');positions=[];uv=[];inds=[]
   for batch in draw['batches']:
    local=native.strip_indices(batch);inds.extend(x+len(positions)for x in local);positions.extend(batch['positions']);require(len(batch.get('uvs',[]))==len(batch['positions']),'native_uv');uv.extend(p[:2]for p in batch['uvs'])
   indices_total+=len(inds);require(indices_total<=1500000 and positions and len(positions)<=1000000,'geometry_budget');normals=[[0.,0.,0.]for _ in positions]
   for k in range(0,len(inds),3):
    a,c,e=[positions[i]for i in inds[k:k+3]];u=[c[j]-a[j]for j in range(3)];v=[e[j]-a[j]for j in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    for i in inds[k:k+3]:normals[i]=[normals[i][j]+n[j]for j in range(3)]
   normals=[[x/math.sqrt(sum(y*y for y in n))for x in n]if sum(y*y for y in n)>1e-24 else[0.,1.,0.]for n in normals];attrs={'POSITION':add(positions,'VEC3','3f',5126),'NORMAL':add(normals,'VEC3','3f',5126),'TEXCOORD_0':add(uv,'VEC2','2f',5126)};primitives.append({'attributes':attrs,'indices':add([(i,)for i in inds],'SCALAR','I',5125),'material':mi,'extras':{'native_external_source_sha256':r['sha256'],'native_material_index':mi}})
  t,q=rest[part['bone']];idx=len(d['nodes']);d['nodes'].append({'name':part['name'],'mesh':len(d['meshes']),'translation':t,'rotation':q,'scale':[1,1,1],'extras':{'nativeBone':part['bone'],'sourceNames':[part['name']],'externalSource':r}});d['meshes'].append({'name':part['name'],'primitives':primitives});d['scenes'][d.get('scene',0)]['nodes'].append(idx);newnodes.append(idx);joins.append({'part':part['name'],'bone':part['bone'],'member':r,'native_mesh_sha256':sha(raw)})
 require(len(joins)==7,'seven_external_parts');d['buffers'][0]['byteLength']=len(b);d['extras']['racerExternalRepair']={'joins':joins,'authority':'Decoded native DAVE names, exact manifest/hash crosscheck, exact NULL part names; no ordinal assignment.','limits':['Existing native paint-neutral inspection fidelity and MC3 manufacturer scale conflict unchanged.','Static rest frames and generated normals retain exporter interpretation; original runtime shading/state not observed.']};source=pack(d,b);(output/'stock-complete-source.glb').write_bytes(source);prepared,descriptor,receipt=prepare(source,'midnight-club-3-remix/vp_corvettez06_03','MC3 Corvette stock repair (source scale conflict)');digest=sha(prepared);(output/(digest+'.glb')).write_bytes(prepared);(output/(digest+'.vehicle')).write_text(descriptor);receipt['external_repair']=d['extras']['racerExternalRepair'];receipt['source_tool_sha256']=sha(reader.read_bytes());(output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--dat',type=Path,required=True);p.add_argument('--source-glb',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--reader',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(repair(a.dat,a.source_glb,a.manifest,a.reader,a.output),indent=2))
