import sys,re,os
from PIL import Image,ImageDraw
d,out,T,rx=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4]
lim=int(sys.argv[5]) if len(sys.argv)>5 else 60
files=sorted(f for f in os.listdir(d) if f.endswith('.png') and re.search(rx,f))[:lim]
cols=max(1,min(len(files),1800//T));rows=(len(files)+cols-1)//cols
sheet=Image.new('RGB',(cols*T,rows*(T+12)),(70,70,70));dr=ImageDraw.Draw(sheet)
for i,f in enumerate(files):
    im=Image.open(os.path.join(d,f)).convert('RGBA');bg=Image.new('RGBA',im.size,(40,40,90,255));bg.alpha_composite(im);im=bg.convert('RGB');im.thumbnail((T,T))
    x,y=(i%cols)*T,(i//cols)*(T+12);sheet.paste(im,(x,y+12));dr.text((x+1,y),f.split('_',2)[-1][:T//6],fill=(255,255,0))
sheet.save(out);print(sheet.size,len(files))
