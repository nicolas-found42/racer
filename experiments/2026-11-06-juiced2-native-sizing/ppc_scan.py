#!/usr/bin/env python3
"""Read-only static PPC scan of the retained decoded Juiced 2 text section.
Usage: ppc_scan.py <pattern>   (stw684 | lwz684 | mult). Never writes outside stdout.
The decoded-section directory defaults to the Oversteer juiced2-recovery copy; set
JUICED2_DECODED_SECTIONS to relocate it. Only the .text section is read.

`mult` finds uses of the 0x824CBE70 multiplier global: a `lis rX,0x824D` (or `lis rX,0x824C` followed by
`ori ..,0xBE70`) and, within WINDOW following words and before rX is rewritten, a memory access or `addi` that
carries the low half 0xBE70 on that same register. Hits are labelled load / store / address-taken (addi/ori)."""
import os,struct,sys
D=os.environ.get('JUICED2_DECODED_SECTIONS','/Users/nicolas/Documents/github/oversteer/artifacts/juiced2-recovery/recompiled-handling/decoded-sections/')
if not D.endswith('/'):D+='/'
BASE=0x82070000
try:
    with open(D+'82070000-.text.bin','rb') as section:
        code=section.read()
except FileNotFoundError as error:
    raise FileNotFoundError(f'{error.filename}: decoded .text section not found; set JUICED2_DECODED_SECTIONS to the decoded-sections directory') from None
words=struct.unpack('>%dI'%(len(code)//4),code[:len(code)//4*4])
def va(i):return BASE+4*i
def find(mask,val):return [va(i) for i,w in enumerate(words) if w&mask==val]

TARGET=0x824CBE70
WINDOW=40
LOADS={32:'lwz',33:'lwzu',34:'lbz',35:'lbzu',40:'lhz',41:'lhzu',42:'lha',43:'lhau',48:'lfs',49:'lfsu',50:'lfd',51:'lfdu'}
STORES={36:'stw',37:'stwu',38:'stb',39:'stbu',44:'sth',45:'sthu',52:'stfs',53:'stfsu',54:'stfd',55:'stfdu'}

def multiplier_uses(words=words,base=BASE,target=TARGET,window=WINDOW):
    """[(va, kind, mnemonic)] for every use of `target` via a lis/disp, lis/addi or lis/ori pair on one register."""
    lo=target&0xFFFF;signed_hi=((target-(lo-0x10000 if lo&0x8000 else lo))>>16)&0xFFFF;ori_hi=(target>>16)&0xFFFF
    out=[]
    for i,w in enumerate(words):
        if w>>26!=15 or (w>>16)&31!=0:continue          # lis rD,imm == addis rD,0,imm
        imm=w&0xFFFF;rd=(w>>21)&31
        if imm not in(signed_hi,ori_hi):continue
        for j in range(i+1,min(i+1+window,len(words))):
            x=words[j];op=x>>26
            if op==15 and (x>>16)&31==0 and (x>>21)&31==rd:break      # rD reloaded: the pair is over
            if (x&0xFFFF)!=lo or (op!=24 and (x>>16)&31!=rd):continue    # base/source register is bits 16-20, except ori whose source is bits 21-25
            if imm==signed_hi and op in LOADS:out.append((base+4*j,'load',LOADS[op]))
            elif imm==signed_hi and op in STORES:out.append((base+4*j,'store',STORES[op]))
            elif imm==signed_hi and op==14:out.append((base+4*j,'address-taken','addi'))
            elif imm==ori_hi and op==24 and (x>>21)&31==rd:out.append((base+4*j,'address-taken','ori'))  # ori rA,rS,UI reads rS (bits 21-25)
    return sorted(set(out))

PATTERNS=('stw684','lwz684','mult')

def main(argv):
    if len(argv)!=2 or argv[1] not in PATTERNS:
        usage=__doc__.splitlines()[1]
        raise SystemExit(usage+(f'\nunknown pattern {argv[1]!r}' if len(argv)==2 else ''))
    which=argv[1]
    if which=='stw684':  # stw rS,684(rA)
        for a in find(0xFC00FFFF,0x900002AC):
            w=words[(a-BASE)//4];print(hex(a),'stw r%d,684(r%d)'%((w>>21)&31,(w>>16)&31))
    elif which=='lwz684':
        for a in find(0xFC00FFFF,0x800002AC):
            w=words[(a-BASE)//4];print(hex(a),'lwz r%d,684(r%d)'%((w>>21)&31,(w>>16)&31))
    else:
        uses=multiplier_uses()
        for a,kind,mnemonic in uses:print(hex(a),kind,mnemonic,hex(words[(a-BASE)//4]))
        print('multiplier uses: loads=%d stores=%d address-taken=%d'%tuple(sum(k==kind for _,k,_ in uses) for kind in('load','store','address-taken')))
    print('text bytes',len(code),file=sys.stderr)

def callers(tgt):
    out=[]
    for i,w in enumerate(words):
        if w>>26==18 and w&2==0:
            off=w&0x03FFFFFC
            if off&0x02000000: off-=0x04000000
            if (BASE+4*i+off)==tgt: out.append((BASE+4*i,'bl' if w&1 else 'b'))
    return out

if __name__=='__main__':main(sys.argv)
