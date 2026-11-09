#!/usr/bin/env python3
"""Decode GT4 gpb2 bundles of Tex1 texture sets to PNG (simple 1-texture/2-transfer sets only).
Formats: gpb2 table (nameoff,dataoff,size,0 x count at 0x10), Tex1 header per Nenkai/GT-File-Specifications
Tex1_TextureSet1.bt. Image transfer = linear PSMT4/PSMT8/PSMCT32/16 rect; palette transfer = PSMCT16/32.
Run with: tools/reversebox/run? (needs only Pillow; uses system python -I with PIL)"""
import struct,sys,json
from pathlib import Path
from PIL import Image
def rgba16(v):
    r=(v&31)<<3;g=((v>>5)&31)<<3;b=((v>>10)&31)<<3;a=255 if v&0x8000 else 0
    return (r|r>>5,g|g>>5,b|b>>5,a)
def decode_set(d):
    assert d[:4]==b'Tex1'
    size=struct.unpack_from('<I',d,12)[0]
    ntex,ntr,pofs,tofs=struct.unpack_from('<HHII',d,0x14)
    tr=[]
    for i in range(ntr):
        off,blk,bw,psm,w,h=struct.unpack_from('<IHBBHH',d,tofs+i*12);tr.append(dict(off=off,blk=blk,bw=bw,psm=psm,w=w,h=h))
    tex=[]
    for i in range(ntex):
        t0,t1,m1,m2,cl=struct.unpack_from('<5Q',d,pofs+i*0x28)
        tex.append(dict(tbp=t0&0x3fff,tbw=(t0>>14)&63,psm=(t0>>20)&63,tw=1<<((t0>>26)&15),th=1<<((t0>>30)&15),cbp=(t0>>37)&0x3fff,cpsm=(t0>>51)&15,csa=(t0>>56)&31,
                        minu=(cl>>4)&0x3ff,maxu=(cl>>14)&0x3ff,minv=(cl>>24)&0x3ff,maxv=(cl>>34)&0x3ff))
    return size,tex,tr
def px(d,t):
    n=t['w']*t['h'];o=t['off'];psm=t['psm']
    if psm==0x14:
        return [ (d[o+i//2]>>(4*(i&1)))&15 for i in range(n)]
    if psm==0x13:return list(d[o:o+n])
    return None
def decode(d):
    size,tex,tr=decode_set(d)
    imgs=[t for t in tr if t['psm'] in(0x13,0x14)]
    pals=[t for t in tr if t['psm'] in(0,2) and t['w']*t['h'] in(16,256)]
    direct=[t for t in tr if t['psm'] in(0,2) and t['w']*t['h']>256]
    meta=dict(size=size,tex=tex,transfers=tr)
    if len(tr)==2 and len(imgs)==1 and len(pals)==1:
        im=imgs[0];pl=pals[0];n=pl['w']*pl['h'];po=pl['off']
        if pl['psm']==2:pal=[rgba16(struct.unpack_from('<H',d,po+2*i)[0]) for i in range(n)]
        else:pal=[tuple(d[po+4*i:po+4*i+3])+(min(255,d[po+4*i+3]*2),) for i in range(n)]
        if n==256:pal=[pal[(i&0xe7)|((i&8)<<1)|((i&16)>>1)] for i in range(256)]
        p=px(d,im);img=Image.new('RGBA',(im['w'],im['h']));img.putdata([pal[i] for i in p]);return img,meta
    if len(tr)==1 and direct:
        t=direct[0];n=t['w']*t['h'];o=t['off']
        if t['psm']==0:data=[tuple(d[o+4*i:o+4*i+3])+(min(255,d[o+4*i+3]*2),) for i in range(n)]
        else:data=[rgba16(struct.unpack_from('<H',d,o+2*i)[0]) for i in range(n)]
        img=Image.new('RGBA',(t['w'],t['h']));img.putdata(data);return img,meta
    return None,meta
def gpb(path,outdir):
    d=Path(path).read_bytes();assert d[:4]==b'gpb2';cnt=struct.unpack_from('<I',d,12)[0];rows=[]
    for i in range(cnt):
        no,do,sz,_=struct.unpack_from('<IIII',d,0x10+16*i);name=d[no:d.index(0,no)].decode()
        blob=d[do:do+sz]
        if blob[:4]!=b'Tex1':rows.append(dict(name=name,kind=blob[:4].hex(),size=sz));continue
        try:img,meta=decode(blob)
        except Exception as e:rows.append(dict(name=name,error=repr(e),size=sz));continue
        if img is None:rows.append(dict(name=name,skipped='layout',transfers=meta['transfers'],size=sz));continue
        p=Path(outdir)/(name if name.endswith('.png') else name+'.png');p.parent.mkdir(parents=True,exist_ok=True);img.save(p)
        rows.append(dict(name=name,w=img.width,h=img.height,file=str(p.name)))
    return rows
if __name__=='__main__':
    res={}
    for src in sys.argv[2:]:
        s=Path(src)
        if s.read_bytes()[:4]!=b'gpb2':continue
        key=s.parent.parent.name+'_'+s.parent.name+'_'+s.stem if s.parent.name in('US','GB') else s.parent.name+'_'+s.stem
        res[str(s)]=gpb(s,Path(sys.argv[1])/s.stem if False else Path(sys.argv[1])/key)
    json.dump(res,open(Path(sys.argv[1])/'decode-report.json','w'),indent=1)
    for k,v in res.items():print(k,sum('file' in r for r in v),'/',len(v))
