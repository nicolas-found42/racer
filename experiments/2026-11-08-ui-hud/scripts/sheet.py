import sys,glob,os
from PIL import Image,ImageDraw
out=sys.argv[1];files=sorted(sys.argv[2:]);cols=int(os.environ.get('COLS',6));cell=int(os.environ.get('CELL',200))
rows=(len(files)+cols-1)//cols;S=Image.new('RGB',(cols*cell,rows*(cell+14)),(60,60,70));dr=ImageDraw.Draw(S)
for i,f in enumerate(files):
    im=Image.open(f).convert('RGBA');sc=min(cell/im.width,cell/im.height,float(os.environ.get('MAXSC',4)));
    im=im.resize((max(1,int(im.width*sc)),max(1,int(im.height*sc))),Image.NEAREST)
    x=(i%cols)*cell;y=(i//cols)*(cell+14)
    bg=Image.new('RGBA',im.size,(110,110,120,255));bg.alpha_composite(im);S.paste(bg.convert('RGB'),(x,y+14));dr.text((x+2,y+1),os.path.basename(f)[:30]+f' {Image.open(f).size}',fill=(255,255,0))
S.save(out)
