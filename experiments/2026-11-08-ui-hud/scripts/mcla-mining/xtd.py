"""Decode Xbox 360 (Xenos) texture from MCLA RSC5 texture dictionary (type 9). Read-only analysis helper."""
import struct, io
import numpy as np
from PIL import Image
FMT={2:('k8',1,1),6:('8888',1,4),18:('DXT1',4,8),19:('DXT3',4,16),20:('DXT5',4,16),49:('DXT5A',4,8),50:('DXN',4,16),
     4:('1555',1,2),3:('565?',1,2),8:('2101010',1,4),10:('88',1,2),36:('?36',1,2)}
def tiled_offsets(wb,hb,log2):
    x=np.arange(wb,dtype=np.int64)[None,:]; y=np.arange(hb,dtype=np.int64)[:,None]
    aw=(wb+31)&~31
    macro=(((y>>5)*(aw>>5))<<(log2+7))
    micro=(((y&6)<<2)<<log2)
    outer=macro+((micro&~0xF)<<1)+(micro&0xF)+((y&8)<<(3+log2))+((y&1)<<4)
    macx=(x>>5)<<(log2+7); micx=(x&7)<<log2
    off=outer+macx+((micx&~0xF)<<1)+(micx&0xF)
    return (((off&~0x1FF)<<3)+((off&0x1C0)<<2)+(off&0x3F)+((y&16)<<7)+(((((y&8)>>2)+(x>>3))&3)<<6))
def parse(body):
    u=lambda a:struct.unpack_from('>I',body,a)[0]
    cnt=struct.unpack_from('>H',body,0x1c)[0]
    arr=u(0x18)&0xfffffff; hashes=u(0x10)&0xfffffff
    out=[]
    for i in range(cnt):
        t=u(arr+4*i)&0xfffffff
        nameptr=u(t+0x18)&0xfffffff; end=body.index(0,nameptr); name=body[nameptr:end].decode('latin1')
        gp=u(t+0x1c)&0xfffffff
        d=[u(gp+0x1c+4*k) for k in range(6)]
        fmt=d[1]&63;endian=(d[1]>>6)&3;base=(d[1]>>12)<<12
        w=(d[2]&0x1fff)+1;h=((d[2]>>13)&0x1fff)+1
        out.append(dict(name=name,hash=u(hashes+4*i),fmt=fmt,endian=endian,base=base&0x0fffffff,w=w,h=h,tiled=d[0]>>31,pitch=(d[0]>>22)&0x1ff,swz=(d[3]>>1)&0xfff,d=d,mips=(d[5]>>0)&0xf))
    return out
def swap(data,endian):
    a=np.frombuffer(data,dtype=np.uint8).copy()
    if endian==1: n=len(a)//2*2;a=a[:n].reshape(-1,2)[:,::-1].reshape(-1)
    elif endian==2: n=len(a)//4*4;a=a[:n].reshape(-1,4)[:,::-1].reshape(-1)
    elif endian==3: n=len(a)//4*4;a=a[:n].reshape(-1,4)[:,[2,3,0,1]].reshape(-1)
    return a
def decode(body,virtual,t):
    name,fmtname=None,None
    f=FMT.get(t['fmt'])
    if not f: return None,'unsupported fmt %d'%t['fmt']
    fname,bs,bpp=f
    w,h=t['w'],t['h']
    wb,hb=(w+bs-1)//bs,(h+bs-1)//bs
    log2=bpp.bit_length()-1
    awb,ahb=(wb+31)&~31,(hb+31)&~31
    need=awb*ahb*bpp
    start=virtual+t['base']
    raw=body[start:start+need]
    if len(raw)<need: raw=raw+b'\0'*(need-len(raw))
    a=swap(raw,t['endian'])
    # tiled, in units of blocks
    unit=a.reshape(-1,bpp) if len(a)%bpp==0 else None
    offs=tiled_offsets(wb,hb,log2)
    idx=(offs//bpp)
    blocks=unit[idx.reshape(-1)] if t['tiled'] or True else None
    blocks=blocks.reshape(hb,wb,bpp)
    if fname=='8888':
        px=blocks.reshape(h,w,4)
        return Image.fromarray(px[...,[0,1,2,3]],'RGBA'),'ok'
    if fname=='k8':
        return Image.fromarray(blocks.reshape(h,w),'L'),'ok'
    if fname in('DXT1','DXT3','DXT5','DXT5A','DXN'):
        lin=blocks.reshape(-1).tobytes()
        cc={'DXT1':b'DXT1','DXT3':b'DXT3','DXT5':b'DXT5','DXT5A':b'ATI1','DXN':b'ATI2'}[fname]
        hdr=bytearray(128);hdr[0:4]=b'DDS ';struct.pack_into('<IIIIII',hdr,4,124,0x81007,h,w,len(lin),0)
        struct.pack_into('<I',hdr,76,32);struct.pack_into('<I',hdr,80,4);hdr[84:88]=cc
        struct.pack_into('<I',hdr,108,0x1000)
        im=Image.open(io.BytesIO(bytes(hdr)+lin));im.load();return im.convert('RGBA') if im.mode!='RGBA' else im,'ok'
    return None,'no decoder '+fname
