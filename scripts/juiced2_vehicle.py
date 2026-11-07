#!/usr/bin/env python3
"""Bounded native Juiced2 350Z geometry recovery; source-derived assembly, explicit tyre adaptation."""
import argparse,hashlib,json,math,struct,zlib,shutil,io,os,stat
from pathlib import Path
from prepare_gt4_vehicle import pack,require,PreparationError
from juiced2_registry import PROFILES,configuration
BASE=0xfd90000
CAR_SECTOR,CAR_SIZE=2285100,8593496
SHARED_SECTOR,SHARED_SIZE=1949278,36217655
sha=lambda b:hashlib.sha256(b).hexdigest()
def filename_hash(name):
 data=name.upper().encode('ascii');result=0
 for i in range(len(data)-1):
  for j in range(i,len(data)):
   a,b=data[i],data[j];result=(result+(b+j)*(b+19)*(a+7)*(a+i))&0xffffffff
 return result%4000000000

def records(header,size):
 require(4<=len(header)<=100000,'header_size');n=struct.unpack_from('>I',header)[0]
 require(len(header)==4+24*n and n<=4096,'header_extent');out={}
 for i in range(n):
  r=struct.unpack_from('>6I',header,4+i*24);require(r[0]not in out and r[1]+r[2]<=size and 0<r[3]<=16000000,'member_range');out[r[0]]=(i,r)
 return out

def mesh(data):
 require(12<=len(data)<=16000000,'mesh_size');n=struct.unpack_from('>I',data)[0];require(3<=n<=1500000 and 8+n*2<=len(data),'index_count');indices=struct.unpack_from('>'+str(n)+'H',data,4);o=4+2*n;ng=struct.unpack_from('>I',data,o)[0];o+=4;require(0<ng<=128,'group_count');groups=[];cursor=0
 for _ in range(ng):
  require(o+108<=len(data),'descriptor_extent');name=data[o:o+32].split(b'\0')[0].decode('ascii');require(name and all(32<=ord(c)<127 for c in name),'material_name');count=struct.unpack_from('>I',data,o+36)[0];nd=struct.unpack_from('>I',data,o+104)[0];require(0<nd<15 and o+116+12*nd<=len(data),'declaration_extent');stride,nv=struct.unpack_from('>2I',data,o+108+12*nd);start=o+116+12*nd;require(12<=stride<=64 and 0<nv<65536 and start+stride*nv<=len(data) and cursor+count<=n,'vertex_extent');positions=[struct.unpack_from('>3f',data,start+i*stride)for i in range(nv)];require(all(math.isfinite(x)and abs(x)<100000 for p in positions for x in p),'position')
  tris=[];strip=[]
  for index in indices[cursor:cursor+count]:
   if index==65535:strip=[];continue
   require(index<nv,'index_range');strip.append(index)
   if len(strip)>=3:
    a,b,c=strip[-3:]
    if len(strip)%2==0:a,b=b,a
    if len({a,b,c})==3:tris.extend((a,b,c))
  require(tris,'empty_triangles');uv=None
  for j in range(nd):
   off,fmt,usage=struct.unpack_from('>3I',data,o+108+j*12)
   if usage>>16==5 and fmt==0x002c235f and off+4<=stride:uv=[struct.unpack_from('>2e',data,start+i*stride+off)for i in range(nv)]
  groups.append({'material':name,'positions':positions,'indices':tris,'uv':uv,'descriptor':o,'stride':stride});cursor+=count;o=start+stride*nv
 # Actual standalone XEMs carry a 44-byte auxiliary bounds trailer.
 # Preserve it in retained source bytes; do not assign unproved semantics.
 require(cursor==n and len(data)-o in (0,44),'mesh_trailing');return groups

def hierarchy(data):
 nodes=[]
 def visit(o,parent,depth):
  require(depth<63 and len(nodes)<4090 and o+140<=len(data),'hierarchy_extent');name=data[o:o+32].split(b'\0')[0].decode('ascii');m=struct.unpack_from('>16f',data,o+32);require(all(math.isfinite(x) for x in m),'matrix');require(all(abs(m[12+j]-v)<1e-5 for j,v in enumerate([0,0,0,1])),'affine');w=[sum(parent[r*4+k]*m[k*4+c]for k in range(4))for r in range(4)for c in range(4)];geom=data[o+100:o+132].split(b'\0')[0].decode('ascii');at=o+(140 if geom!='NONE' else 136);require(at+4<=len(data),'child_header');n=struct.unpack_from('>I',data,at)[0];require(n<=128,'child_count');nodes.append({'name':name,'geometry':geom,'matrix':w,'offset':o});o=at+4
  for _ in range(n):o=visit(o,w,depth+1)
  return o
 require(visit(0,[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],0)==len(data),'hierarchy_trailing');return nodes

def texture(data):
 from PIL import Image
 require(len(data)>=40,'texture_header');fmt,w,h=struct.unpack_from('>3I',data);require(0<w<=2048 and 0<h<=2048,'texture_dimensions');kind=fmt&63
 if kind not in (18,19,20):return None
 pitch=8 if kind==18 else 16;raw=data[40:];raw=bytes(v for pair in zip(raw[1::2],raw[0::2])for v in pair);width=(w+3)//4;height=(h+3)//4;aligned=(width+31)&~31;log=(pitch>>2)+((pitch>>1)>>(pitch>>2));out=bytearray(width*height*pitch)
 for offset in range(len(raw)//pitch):
  ob=offset<<log;ot=((ob&~4095)>>3)+((ob&1792)>>2)+(ob&63);om=ot>>(7+log);mx=(om%(aligned>>5))<<2;tile=(((ot>>(5+log))&2)+(ob>>6))&3;x=((mx+tile)<<3)+((((ot>>1)&~15)+(ot&15))&((pitch<<3)-1))//pitch;my=(om//(aligned>>5))<<2;tile=((ot>>(6+log))&1)+((ob&2048)>>10);micro=(((ot&(((pitch<<6)-1)&~31))+((ot&15)<<1))>>(3+log))&~1;y=((my+tile)<<3)+micro+((ot&16)>>4)
  if x<width and y<height:out[(y*width+x)*pitch:(y*width+x+1)*pitch]=raw[offset*pitch:(offset+1)*pitch]
 fourcc={18:b'DXT1',19:b'DXT3',20:b'DXT5'}[kind];header=struct.pack('<7I',124,0x81007,h,w,len(out),0,1)+b'\0'*44+struct.pack('<II4s5I',32,4,fourcc,0,0,0,0,0)+struct.pack('<5I',0x1000,0,0,0,0);im=Image.open(io.BytesIO(b'DDS '+header+out)).convert('RGBA');dest=io.BytesIO();im.save(dest,format='PNG');return dest.getvalue()

def profile_surface(data,segments=64,steps=8):
 """Candidate cubic-contour revolution, not recovered native tessellation/shader."""
 require(len(data)==596 and data[:32].split(b'\0')[0]==b'TYRE_PROFILE','profile_identity')
 require(struct.unpack_from('>2I',data,96)==(3,13),'profile_layout')
 require(type(segments)is int and 8<=segments<=128 and type(steps)is int and 1<=steps<=16,'profile_budget')
 knots=[[struct.unpack_from('>3f',data,104+i*36+j*12)for j in range(3)]for i in range(13)]
 require(all(math.isfinite(x)for knot in knots for p in knot for x in p),'profile_finite')
 require(all(abs(p[2])<.001 and 0<p[1]<100 and abs(p[0])<100 for knot in knots for p in knot),'profile_plane')
 contour=[]
 for i in range(12):
  controls=[knots[i][0],knots[i][2],knots[i+1][1],knots[i+1][0]]
  for j in range(steps):
   t=j/steps;weights=[(1-t)**3,3*(1-t)**2*t,3*(1-t)*t*t,t**3];contour.append([sum(weights[k]*controls[k][c]for k in range(4))for c in range(2)])
 contour.append(list(knots[-1][0][:2]));positions=[];indices=[]
 for x,radius in contour:
  for j in range(segments):
   angle=2*math.pi*j/segments;positions.append([x/100,radius*math.cos(angle)/100,radius*math.sin(angle)/100])
 for i in range(len(contour)-1):
  for j in range(segments):
   a=i*segments+j;b=i*segments+(j+1)%segments;c=a+segments;d=b+segments;indices.extend([a,c,b,b,c,d])
 return {'positions':positions,'indices':indices,'knots':knots,'source_sha256':sha(data),'interpretation':'Candidate cubic Bezier anchor/in/out triples revolved around nativeX; native curve interpolation, tessellation, UV and tyre shader rest deformation not independently recovered.'}

def build(iso,car_header,output,stock_brakes=False,car='350Z',*,retain_members=True):
 require(car in PROFILES,'car_profile');profile=PROFILES[car];require(len(car_header)==profile['header_bytes'] and sha(car_header)==profile['header_sha256'],'header_pin')
 require(not output.exists() and not output.is_symlink() and not any(p.is_symlink()for p in output.parents),'output_exists');require(iso.is_file() and not iso.is_symlink(),'iso_regular');require(shutil.disk_usage(output.parent).free>=20*1024**3,'disk_budget');output.mkdir(mode=0o700);sources=[];cache={};total=packed_total=0;vertex_work=index_work=0
 with iso.open('rb')as f:
  initial_stat=os.fstat(f.fileno());require(stat.S_ISREG(initial_stat.st_mode),'iso_regular')
  f.seek(BASE+profile['header_sector']*2048);require(f.read(len(car_header))==car_header,'source_header_pair');config_evidence=configuration(f,profile,BASE,filename_hash,require)
  f.seek(BASE+1949258*2048);shared_header=f.read(39436);require(sha(shared_header)=='abe96c6f9d9c6422f6fd619436a99efaee12102be4bccc388757fedcbbc62ac2','shared_header_pin');banks=[(profile['bank'],profile['sector'],records(car_header,profile['size'])),('shared',SHARED_SECTOR,records(shared_header,SHARED_SIZE))]
  def get(key,bank=None):
   nonlocal total,packed_total
   for name,sector,rows in banks:
    if bank and name!=bank:continue
    if key not in rows:continue
    if (name,key)in cache:return cache[name,key]
    ordinal,row=rows[key];packed_total+=row[2];require(row[2]<=16000000 and packed_total+profile['script_record'][2]<=32*1024**2,'packed_budget');require(total+row[3]+profile['script_record'][3]<=128*1024**2,'decoded_budget');f.seek(BASE+sector*2048+row[1]);p=f.read(row[2]);require(len(p)==row[2],'read_extent')
    if row[2]==row[3]:b=p
    else:
     z=zlib.decompressobj();b=z.decompress(p,row[3]+1);require(z.eof and not z.unused_data and len(b)==row[3],'decompression')
    total+=len(b);require(total<=128*1024**2,'decoded_budget');cache[name,key]=b
    if retain_members:(output/f'{name}-{ordinal}.bin').write_bytes(b)
    sources.append({'bank':name,'ordinal':ordinal,'key':key,'record':row,'sha256':sha(b),'packed_sha256':sha(p),'iso_offset':BASE+sector*2048+row[1]});return b
   return None
  hb=get(filename_hash(profile['hierarchy']),profile['bank']);require(hb is not None and sha(hb)==profile['hierarchy_sha256'],'hierarchy_identity')
  require(hb is not None,'hierarchy_missing');nodes=hierarchy(hb);require(nodes[0]['name']==car+'_ROOT','hierarchy_root_join');pivots={n['name']:n['matrix'][3:12:4]for n in nodes if n['name'].startswith('WHEEL_')};require(set(pivots)=={'WHEEL_FL','WHEEL_FR','WHEEL_RL','WHEEL_RR'},'four_pivots')
  selection=None
  if car not in ('350Z','MX5'):
   from juiced2_cohort import assembly_contract
   standards={row['fields'][1]['value']:row['fields'][2]['value']for row in config_evidence['typed']['lines']if len(row['fields'])>=3 and row['fields'][0]['value']=='STANDARD'}
   selection=assembly_contract(car,nodes,standards,banks[0][2],banks[1][2],filename_hash)
   require(selection['status']=='static_selector_supported','cohort_static_contract')
  doc={'asset':{'version':'2.0','generator':'Racer native Juiced2 XEM recovery'},'scene':0,'scenes':[{'nodes':[]}],'nodes':[],'meshes':[],'materials':[],'accessors':[],'bufferViews':[],'images':[],'textures':[]};binary=bytearray();groups=[];clouds={-1:[]};matcache={};texcache={}
  def add(values,typ,fmt,component):
   binary.extend(b'\0'*(-len(binary)%4));start=len(binary)
   for v in values:binary.extend(struct.pack('<'+fmt,*v))
   doc['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(binary)-start});a={'bufferView':len(doc['bufferViews'])-1,'componentType':component,'count':len(values),'type':typ}
   if typ=='VEC3':a.update(min=[min(v[k]for v in values)for k in range(3)],max=[max(v[k]for v in values)for k in range(3)])
   doc['accessors'].append(a);return len(doc['accessors'])-1
  def material(name,uv):
   cache_key=(name,bool(uv))
   if cache_key in matcache:return matcache[cache_key]
   color=[.32,.35,.4,1] if 'BODY'in name.upper()else[.08,.08,.08,1]
   if 'GLASS'in name.upper():color=[.08,.12,.16,.65]
   m={'name':name,'doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':color,'roughnessFactor':.55,'metallicFactor':.15}}
   if color[3]<1:m['alphaMode']='BLEND'
   tb=get(filename_hash('Textures\\'+name+'.ddt'))
   if tb and uv:
    png=texture(tb)
    if png:
     binary.extend(b'\0'*(-len(binary)%4));doc['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(png)});binary.extend(png);doc['images'].append({'bufferView':len(doc['bufferViews'])-1,'mimeType':'image/png'});doc['textures'].append({'source':len(doc['images'])-1});m['pbrMetallicRoughness'].update(baseColorFactor=[1,1,1,1],baseColorTexture={'index':len(doc['textures'])-1})
   index=len(doc['materials']);doc['materials'].append(m);matcache[cache_key]=index;return index
  def emit(name,data,matrix,wheel=-1,mirror=False,materials=None):
   nonlocal vertex_work,index_work
   prim=[]
   for g in mesh(data):
    if materials is not None and g['material']not in materials:continue
    if g['material'].upper().startswith(('NO_BUMPERS','NO_SSKIRTS')):continue
    vertex_work+=len(g['positions']);index_work+=len(g['indices']);require(vertex_work<=1000000 and index_work<=1500000,'expanded_geometry_budget')
    ps=[]
    for p in g['positions']:
     q=[(-p[0] if mirror else p[0]),p[1],p[2],1];ps.append([sum(matrix[k*4+j]*q[j]for j in range(4))/100 for k in range(3)])
    inds=g['indices'][:]
    if mirror:
     for i in range(0,len(inds),3):inds[i+1],inds[i+2]=inds[i+2],inds[i+1]
    normals=[[0.,0.,0.]for _ in ps]
    for i in range(0,len(inds),3):
     a,b,c=[ps[j]for j in inds[i:i+3]];u=[b[k]-a[k]for k in range(3)];v=[c[k]-a[k]for k in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
     for j in inds[i:i+3]:normals[j]=[normals[j][k]+n[k]for k in range(3)]
    normals=[[x/max(math.sqrt(sum(t*t for t in n)),1e-12)for x in n]for n in normals];attrs={'POSITION':add(ps,'VEC3','3f',5126),'NORMAL':add(normals,'VEC3','3f',5126)}
    if g['uv']:attrs['TEXCOORD_0']=add(g['uv'],'VEC2','2f',5126)
    prim.append({'attributes':attrs,'indices':add([(x,)for x in inds],'SCALAR','I',5125),'material':material(g['material'],g['uv'])});clouds.setdefault(wheel,[]).extend(ps)
   if prim:
    require(len(doc['nodes'])<4096,'node_budget')
    idx=len(doc['nodes']);doc['nodes'].append({'name':name,'mesh':len(doc['meshes'])});doc['meshes'].append({'name':name,'primitives':prim});doc['scenes'][0]['nodes'].append(idx);groups.append((idx,wheel))
  for node in nodes:
   name=node['name'];geom=node['geometry']
   if geom=='NONE' or any(x in name for x in ['_DEAD','LIGHTSON','BRKLIGHT']):continue
   data=get(filename_hash('mesh\\'+geom+'.xem'));require(data is not None,'body_mesh_missing');emit(name,data,node['matrix'])
  rim=get(filename_hash(profile['rim']),profile['bank']);tyre=get(641716538,'shared');require(rim and tyre and sha(rim)==profile['rim_sha256'],'wheel_missing')
  tyre_filter=None
  if selection:
   from juiced2_cohort import tyre_materials
   tyre_filter=tyre_materials(tyre,mesh)
   selection['shared_toyo_policy']={'source_sha256':sha(tyre),'selected_materials':list(tyre_filter),'excluded_materials':['OZ_MICHELANGELO','brake_disc','BLACK2'],'authority':'Exact pinned composite groups; only explicit rubber group adapted. Native procedural tyre sizing remains unknown.'}
  for i,label in enumerate(['FL','FR','RL','RR']):
   c=pivots['WHEEL_'+label];m=[1,0,0,c[0],0,1,0,c[1],0,0,1,c[2],0,0,0,1];emit('WHEEL_'+label,rim,m,i,label.endswith('L'));emit('ADAPTED_NATIVE_TOYO_TYRE_'+label,tyre,m,i,label.endswith('L'),tyre_filter)
   if stock_brakes:
    # Native8210FD90 appends _L for wheel indices0/2 and _R for1/3.
    side='_L' if label.endswith('L') else '_R'
    for stem,role in [('TEST_DISC',i),('TEST_CALLIPER',-1)]:
     name=stem+side;part=get(filename_hash('mesh\\'+name+'.xem'),'shared');require(part is not None,'stock_brake_missing');emit(name+'_'+label,part,m,role,label.endswith('L'))
  lift=max(0,-min(p[1]for ps in clouds.values()for p in ps));require(lift<.1,'ground_lift')
  # Bake uniform rest lift into every position accessor, including descriptor centers.
  for a in doc['accessors']:
   if a['type']!='VEC3' or 'min'not in a:continue
   # NORMAL accessors also have extrema: identify only POSITION references.
   ids={pr['attributes']['POSITION']for me in doc['meshes']for pr in me['primitives']}
   if doc['accessors'].index(a)not in ids:continue
   v=doc['bufferViews'][a['bufferView']]
   for j in range(a['count']):off=v['byteOffset']+12*j+4;y=struct.unpack_from('<f',binary,off)[0];struct.pack_into('<f',binary,off,y+lift)
   a['min'][1]+=lift;a['max'][1]+=lift
  body=[min(p[k]for p in clouds[-1])+(lift if k==1 else 0)for k in range(3)]+[max(p[k]for p in clouds[-1])+(lift if k==1 else 0)for k in range(3)];wheels=[]
  for i,label in enumerate(['FL','FR','RL','RR']):
   c=[x/100 for x in pivots['WHEEL_'+label]];radius=max(math.hypot(p[1]-c[1],p[2]-c[2])for p in clouds[i]);width=2*max(abs(p[0]-c[0])for p in clouds[i]);c[1]+=lift;wheels.append({'center':c,'radius':radius,'width':width})
  limits=['Native car source hierarchy/mounts and actual meshes; static state selection excludes damaged/emissive alternatives by explicit source names.','Shared native Toyo tyre mesh is an explicit fitting adaptation; stock TYRE_PROFILE procedural runtime generation is not recovered. No silent claim of stock tyre parity.','Native centimetre-to-metre interpretation is explicit and wheelbase-plausible; original runtime units/scale and wheel orientation controls not independently traced.','Left wheel X reflection is explicit orientation adaptation; original runtime side handling unresolved.','Native texture top mip and recognized half-float UV only; native shading/normal declarations/material effects not reproduced.']
  if stock_brakes:limits.append('Configured TEST_DISC/TEST_CALLIPER side-suffixed source meshes added at native hubs; disc spins with wheel, caliper uses a wheel carrier that steers without rolling. Original brake scale/orientation remain unverified.')
  doc['buffers']=[{'byteLength':len(binary)}];doc['extras']={'sourceGame':'Juiced2 Xbox360','sources':sources,'hierarchy_sha256':sha(hb),'native_wheel_pivots':pivots,'units':'100native units/metre conversion','limitations':limits}
  if car!='350Z':doc['extras']['sourceCarConfiguration']=config_evidence
  if selection:doc['extras']['sourceAssemblySelection']=selection
  glb=pack(doc,binary);digest=sha(glb);desc=['RACER_VEHICLE 1','id "vehicle-'+digest+'"','name '+json.dumps(profile['name']),'mesh "'+digest+'.glb"','sha256 '+digest,'source_sha256 '+sha(hb),'body '+' '.join(map(str,body))]
  desc+=['wheel '+label+' '+' '.join(map(str,w['center']+[w['radius'],w['width']]))for label,w in zip(['FL','FR','RL','RR'],wheels)];desc+=['groups '+str(len(groups))]+['group '+str(n)+' '+str(w)for n,w in groups];
  binding_roles=[]
  if stock_brakes:
   desc[0]='RACER_VEHICLE 2'
   first=desc.index('groups '+str(len(groups)))+1
   for j,(node,wheel)in enumerate(groups):
    name=doc['nodes'][node]['name'];role='body'
    if name.startswith('TEST_CALLIPER'):role='carrier '+name[-2:]
    elif wheel>=0:role='wheel '+['FL','FR','RL','RR'][wheel]
    desc[first+j]='group '+str(node)+' '+role;binding_roles.append({'node':node,'role':role})
  final_stat=os.fstat(f.fileno());require((initial_stat.st_dev,initial_stat.st_ino,initial_stat.st_size,initial_stat.st_mtime_ns)==(final_stat.st_dev,final_stat.st_ino,final_stat.st_size,final_stat.st_mtime_ns),'iso_changed');report={'binding_roles':binding_roles,'iso_path':str(iso.resolve()),'iso_size':initial_stat.st_size,'iso_mtime_ns':initial_stat.st_mtime_ns,'iso_hash':'unknown: complete image not freshly hashed','car_header_sha256':sha(car_header),'shared_header_sha256':sha(shared_header),'packed_selected_bytes':packed_total,'decoded_selected_bytes':total,'prepared_sha256':digest,'body':body,'wheels':wheels,'groups':groups,'native_wheel_pivots':pivots,'wheelbase':(pivots['WHEEL_FL'][2]-pivots['WHEEL_RL'][2])/100,'sources':sources,'limitations':limits,'textures':len(doc['images']),'vertices':sum(len(v)for v in clouds.values())};(output/(digest+'.glb')).write_bytes(glb);(output/(digest+'.vehicle')).write_text('\n'.join(desc)+'\n');(output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--iso',type=Path,required=True);p.add_argument('--header',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--stock-brakes',action='store_true');p.add_argument('--car',choices=tuple(PROFILES),default='350Z');a=p.parse_args();print(json.dumps(build(a.iso,a.header.read_bytes(),a.output,a.stock_brakes,a.car),indent=2))
