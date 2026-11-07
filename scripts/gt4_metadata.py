#!/usr/bin/env python3
"""Bounded read-only GT4 EU SpecDB metadata audit; no model or runtime promotion.

Format authority: retained Nenkai/PDTools commit 2a9637d8c36100e4c211d73cd8140a9d690578d2
Table.cs, DBT_DatabaseTable.cs, SDB_StringDatabase.cs and mapping schemas.
This independent reader does not import or execute the quarantined gt4_specdb.py.
"""
import argparse,collections,hashlib,json,math,struct
from pathlib import Path
MAX_FILE=16*1024**2
MANIFEST_SHA256='6809009a63f69e6fe6c069c86e5fbee88f0a7944852800701adf3969b0f3b40c'

def need(ok,reason):
    if not ok:raise ValueError(reason)

def read(path,expected=None):
    path=Path(path);need(not path.is_symlink() and path.is_file(),'regular_input')
    with path.open('rb')as f:data=f.read(MAX_FILE+1)
    need(len(data)<=MAX_FILE,'file_budget')
    if expected:need(hashlib.sha256(data).hexdigest()==expected,'input_pin')
    return data

def u32(data,at):
    need(0<=at<=len(data)-4,'word_bounds');return struct.unpack_from('<I',data,at)[0]

def string_at(data,at):
    need(0<=at<len(data),'string_bounds');end=data.find(b'\0',at,min(len(data),at+4096));need(end>=at,'string_terminator');return data[at:end].decode('utf-8')

def strings(data):
    need(data[:4]==b'GTST' and u32(data,8)==1,'GTST_little_endian');count=u32(data,4);base=16+count*4;need(count<=100000 and base<=len(data),'string_count')
    return [string_at(data,base+u32(data,16+4*i)+2)for i in range(count)]

def labels(data):
    need(data[:4]==b'GTID','GTID');count=u32(data,4);base=16+8*count;need(count<=100000 and base<=len(data),'label_count');result={}
    for i in range(count):
        offset,key=struct.unpack_from('<II',data,16+8*i);need(key not in result,'duplicate_label_id');result[key]=string_at(data,base+offset+2)
    return u32(data,12),result

class Table:
    def __init__(self,data,idi):
        need(data[:4]==b'GTDB' and len(data)>=16,'GTDB');self.data=data;self.table_id,self.labels=labels(idi)
        self.flags,aligned,self.count,self.width=struct.unpack_from('<HHII',data,4)
        need(self.flags<256 and 0<self.count<=100000 and 0<self.width<=4096,'table_header')
        need(self.count*self.width<=MAX_FILE,'decoded_table_budget')
        end=16+8*self.count;need(end<=len(data),'row_index_bounds');self.entries=[struct.unpack_from('<II',data,16+8*i)for i in range(self.count)];self.stats=collections.Counter()
        self.templates=None;self.longcodes={}
        if self.flags&1:
            book=end;block=u32(data,book);codes=u32(data,book+4)
            need(codes<=256 and block>=0x208+8*codes and book+block<=len(data),'codebook_bounds')
            self.lookup=data[book+8:book+0x208]
            for i in range(codes):
                at=book+0x208+i*8;bits,value=data[at:at+2];code=u32(data,at+4);need(1<=bits<32 and code<(1<<bits),'huffman_code');need((bits,code)not in self.longcodes,'duplicate_huffman_code');self.longcodes[bits,code]=value
            template_header=book+block;offset=u32(data,template_header);need(offset>=8 and template_header+offset<=len(data),'template_bounds');self.templates=data[template_header+8:template_header+offset];self.start=template_header+offset
        else:self.start=end
        offsets=sorted(set(off for _,off in self.entries));need(all(off<len(data)-self.start for off in offsets),'row_offsets')
        self.ends={off:(offsets[i+1]if i+1<len(offsets)else len(data)-self.start)for i,off in enumerate(offsets)}
    def row(self,index):
        key,off=self.entries[index];raw=self.data[self.start+off:self.start+self.ends[off]]
        if not self.flags&1:
            need(len(raw)>=self.width,'raw_row_bounds');self.stats['raw']+=1;return key,raw[:self.width]
        count=raw[0];need(count>0,'empty_huffman_row');bit=0;decoded=[]
        for _ in range(count):
            byte=bit//8;shift=bit%8;word=int.from_bytes(raw[1+byte:5+byte].ljust(4,b'\0'),'little')>>shift
            value,used=self.lookup[(word&255)*2:(word&255)*2+2]
            if not used:
                matches=[(bits,self.longcodes[bits,word&((1<<bits)-1)])for bits in range(9,32)if(bits,word&((1<<bits)-1))in self.longcodes]
                need(len(matches)==1,'huffman_symbol');used,value=matches[0]
            else:need(used<=8,'lookup_code_size')
            bit+=used;need(bit<=8*(len(raw)-1),'huffman_bits_outside_row');decoded.append(value)
        tag=decoded[0];kind=tag>>6;slot=tag&63;self.stats[str(kind)]+=1
        if kind==1:need(len(decoded)>=1+self.width,'literal_row_short');return key,bytes(decoded[1:1+self.width])
        need(kind in(0,2),'compression_kind');base=slot*self.width;need(base+self.width<=len(self.templates),'template_slot');row=bytearray(self.templates[base:base+self.width])
        if kind==2:
            maskbytes=(self.width+7)//8;need(len(decoded)>=1+maskbytes,'patch_mask_short');cursor=1+maskbytes
            for j in range(self.width):
                if decoded[1+j//8]&(1<<(j%8)):
                    need(cursor<len(decoded),'patch_value_short');row[j]=decoded[cursor];cursor+=1
            need(cursor==len(decoded),'patch_unused_symbols')
        return key,bytes(row)
    def rows(self):return [self.row(i)for i in range(self.count)]

def unique(rows):
    result={}
    for key,value in rows:need(key not in result,'duplicate_row_id');result[key]=value
    return result

def join_specs(folder,manifest):
    manifest=json.loads(read(manifest,MANIFEST_SHA256));pins={r['file']:r['sha256']for r in manifest['files']};folder=Path(folder)
    def get(name):return read(folder/name,pins[name])
    names=('GENERIC_CAR','DEFAULT_PARTS','CHASSIS','FRONTTIRE','REARTIRE','TIRESIZE','CAR_VARIATION_british','VARIATIONbritish','CAR_NAME_british')
    tables={name:Table(get(name+'.dbt'),get(name+'.idi'))for name in names};need(sum(t.count*t.width for t in tables.values())<=32*1024**2,'decoded_batch_budget');values={name:table.rows()for name,table in tables.items()};byid={n:unique(rows)for n,rows in values.items()if n!='VARIATIONbritish'};text=strings(get('british_StrDB.sdb'))
    def textid(i):need(i<len(text),'string_id');return text[i]
    variation=collections.defaultdict(list)
    for key,row in values['VARIATIONbritish']:variation[key].append(row)
    cv=tables['CAR_VARIATION_british'];variation_by_label={cv.labels[k]:(k,row)for k,row in values['CAR_VARIATION_british']}
    nm=tables['CAR_NAME_british'];names_by_label={nm.labels[k]:textid(u32(row,0))for k,row in values['CAR_NAME_british']}
    output={}
    for key,row in values['GENERIC_CAR']:
        label=tables['GENERIC_CAR'].labels[key];cvkey,cvrow=variation_by_label[label];varid,vartable=struct.unpack_from('<II',cvrow);need(vartable==tables['VARIATIONbritish'].table_id,'variation_table_join');vars=variation[varid]
        models={textid(u32(v,0))for v in vars};need(len(models)==1,'variation_model_identity');model=next(iter(models));need(model not in output,'model_duplicate')
        partkey,parttable=struct.unpack_from('<II',row);need(parttable==tables['DEFAULT_PARTS'].table_id,'default_parts_table_join');parts=byid['DEFAULT_PARTS'][partkey];need(len(parts)%8==0,'parts_key_width');keys={}
        for off in range(0,len(parts),8):
            k,t=struct.unpack_from('<II',parts,off)
            if t in [tables[n].table_id for n in('CHASSIS','FRONTTIRE','REARTIRE')]:need(t not in keys,'duplicate_default_table');keys[t]=k
        chassiskey=keys[tables['CHASSIS'].table_id];chassis=byid['CHASSIS'][chassiskey];need(len(chassis)>=37,'chassis_schema');shorts=struct.unpack_from('<13h',chassis)
        tires={}
        for axle,table in(('front','FRONTTIRE'),('rear','REARTIRE')):
            tirekey=keys[tables[table].table_id];sizekey,sizetable=struct.unpack_from('<II',byid[table][tirekey]);need(sizetable==tables['TIRESIZE'].table_id,'tire_size_table_join');size=byid['TIRESIZE'][sizekey];need(len(size)==4,'tiresize_schema');tires[axle]={'tire_row_id':tirekey,'size_row_id':sizekey,'flatness_raw':size[0],'category_raw':size[1],'diameter_raw':size[2],'width_raw':size[3]}
        bounds={tuple(struct.unpack_from('<4f',v,16))for v in vars};need(len(bounds)==1,'variation_bounds_disagree');bounds=list(next(iter(bounds)));need(all(math.isfinite(v)for v in bounds),'variation_bounds_nonfinite')
        output[model]={'generic_row_id':key,'label':label,'name':names_by_label.get(label),'year_raw':struct.unpack_from('<h',row,12)[0],'default_parts_row_id':partkey,'car_variation_row_id':cvkey,'variation_row_id':varid,'chassis_row_id':chassiskey,'chassis_raw':dict(zip(('length','height','wheelbase','mass','dlength','dheight','dmass','performanceF','performanceR','treadF','treadR','width','dwidth'),shorts)),'chassis_flags':dict(zip(('category','cartype','percentageF','yaw','cheight','WheelLayout','GrowInch','TireWidthR','FrontStiffness','RearStiffness','GasCapacity'),chassis[26:37])),'variation_model_bounds_raw':bounds,'factory_paint_rows':len(vars),'tires_raw':tires}
    return {'source_build':manifest['source_build'],'models':output,'tables':{name:{'table_id':t.table_id,'rows':t.count,'row_bytes':t.width,'compression_kinds':dict(t.stats),'dbt_sha256':pins[name+'.dbt'],'idi_sha256':pins[name+'.idi']}for name,t in tables.items()},'limits':['Raw schema fields from GT4 EU2560 database; no manufacturer specification or native runtime behavior claim.','CHASSIS width/dwidth field names are PDTools schema labels, not independently established physical semantics.','Tire byte physical scaling and special historic encodings are not inferred here.','VARIATION repeated row IDs preserved as paint rows; unique-key tables reject duplicates.']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=join_specs(a.folder,a.manifest);payload=json.dumps(r,indent=2,allow_nan=False)+'\n';need(len(payload.encode())<=16*1024**2,'output_budget')
    with a.output.open('x')as f:f.write(payload)
    print(json.dumps({'models':len(r['models']),'tables':r['tables']}))
if __name__=='__main__':main()
