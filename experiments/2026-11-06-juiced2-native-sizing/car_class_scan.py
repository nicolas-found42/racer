#!/usr/bin/env python3
"""Attribute stores to +176/+192 to the car class: functions that also touch car-only high offsets 9656..9668."""
from ppc_scan import words,BASE
starts=[i for i,w in enumerate(words) if w==0x7d8802a6]   # mflr r12 prologue marker
starts.append(len(words))
def disp(w):
    d=w&0xFFFF;return d-0x10000 if d&0x8000 else d
MEM={32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55}
out=[]
for a,b in zip(starts,starts[1:]):
    st=[];hi=[]
    for i in range(a,b):
        w=words[i];op=w>>26
        if op in MEM:
            d=disp(w)
            if op in (52,36) and d in(176,192):st.append((BASE+4*i,'stfs' if op==52 else 'stw',d,(w>>21)&31,(w>>16)&31))
            if 9656<=d<=9668:hi.append(BASE+4*i)
    if st and hi:out.append((BASE+4*a,len(hi),st))
print(len(starts),'functions;',len(out),'touch both')
for f,n,st in out:print(hex(f),n,[(hex(x[0]),x[1],x[2],'f%d'%x[3],'r%d'%x[4]) for x in st])
