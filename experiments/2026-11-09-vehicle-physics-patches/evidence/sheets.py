import sys,os
from PIL import Image,ImageDraw
S=sys.argv[1]; M=S+'/matrix'
names={0:"Acura NSX '04 (12.8 cm)",2:"Mustang '73 (21.6 cm)",7:"Dodge RAM (22.3 cm)",8:"Daihatsu Midget (17.4 cm)",12:"Ford GT (10.3 cm)",16:"Juiced 2 CCX (8.6 cm)"}
def sheet(prefix,cars,views,out,w=504,h=279):
    pad=26
    im=Image.new('RGB',(pad*5+len(views)*w+90, pad*2+len(cars)*(h+pad)),(20,20,24))
    d=ImageDraw.Draw(im)
    for j,v in enumerate(views): d.text((pad*3+90+j*w,6),v,fill=(230,230,230))
    for i,c in enumerate(cars):
        y=pad*2+i*(h+pad)
        d.text((4,y+h//2),names[c][:16]+"\n"+names[c][16:],fill=(230,230,230))
        for j,v in enumerate(views):
            f=f"{M}/{prefix}-c{c}-{v}.ppm"
            if os.path.exists(f):
                t=Image.open(f).convert('RGB').resize((w,h),Image.LANCZOS); im.paste(t,(pad*3+90+j*w,y))
    im.save(f"{S}/{out}",quality=85)
sheet('ramp',[0,2,7,8,12,16],['rear','left','front','elevated'],'sheet-ramp.jpg')
sheet('brake',[0,2,7,8,12,16],['left','front'],'sheet-brake.jpg')
sheet('corner',[0,2,7,8,12,16],['rear','right','elevated'],'sheet-corner.jpg')
print("sheets done")
