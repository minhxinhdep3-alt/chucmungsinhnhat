#!/usr/bin/env python3
"""
make_video.py – Thêm pháo hoa + giấy pháo + lời chúc + nhạc Happy Birthday vào video có sẵn.

Cách dùng:
  pip install numpy opencv-python pillow      (và cài ffmpeg)
  python make_video.py video_goc.mp4 birthday_video.mp4
  python make_video.py video_goc.mp4 out.mp4 --party 7.0 --name "Công Chúa"
  python make_video.py video_goc.mp4 out.mp4 --preview      # chỉ xuất vài ảnh xem thử (prev_*.png)

Tùy chọn:
  --party   giây bắt đầu tiệc (pháo hoa/giấy/chữ). Mặc định 7.0
  --song    giây bắt đầu nhạc. Mặc định = party - 0.1
  --name    tên hiện ở câu chúc cuối
  --font    đường dẫn font .ttf hỗ trợ tiếng Việt (mặc định tự tìm DejaVu Sans Bold)
Video đầu vào sẽ được chuẩn hóa về 1280x720, 24fps.
"""
import argparse, os, glob, wave, subprocess, sys, math, random
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ap=argparse.ArgumentParser()
ap.add_argument("input"); ap.add_argument("output",nargs="?",default="birthday_video.mp4")
ap.add_argument("--party",type=float,default=7.0); ap.add_argument("--song",type=float,default=None)
ap.add_argument("--name",default="Công Chúa"); ap.add_argument("--font",default=None)
ap.add_argument("--preview",action="store_true")
ARGS=ap.parse_args()
V=ARGS.input
def probe_dur():
    r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",V],capture_output=True,text=True)
    return float(r.stdout.strip())
DUR=probe_dur()
W,H,FPS=1280,720,24
NF=int(DUR*FPS)
random.seed(7); np.random.seed(7)
PARTY=ARGS.party
PREVIEW=ARGS.preview
PREV_T=[PARTY+.3,PARTY+1.5,PARTY+3,PARTY+6,PARTY+11,DUR-1.5]

COL=[(255,95,168),(255,216,107),(110,231,255),(157,123,255),(124,242,154),(255,138,92),(255,255,255)]
NAME=ARGS.name
WISHES=["Luôn xinh đẹp và hạnh phúc","Mọi điều ước đều thành sự thật","Tuổi mới thật nhiều niềm vui","Mãi là công chúa của chúng mình","Sức khỏe, bình an, may mắn","Yêu bạn nhiều lắm"]
# (bắt đầu, kết thúc, sprite)
def find_font():
    if ARGS.font: return ARGS.font
    c=["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf","C:/Windows/Fonts/arialbd.ttf","C:/Windows/Fonts/segoeuib.ttf","/System/Library/Fonts/Supplemental/Arial Bold.ttf","/Library/Fonts/Arial Bold.ttf"]
    for p in c:
        if os.path.exists(p): return p
    g=glob.glob("/usr/share/fonts/**/*Bold*.ttf",recursive=True)
    if g: return g[0]
    sys.exit("Không tìm thấy font, hãy dùng --font duong_dan.ttf")
FB=find_font()

def heart_pts(cx,cy,s,rot=0,n=26):
    t=np.linspace(0,2*np.pi,n,endpoint=False)
    x=16*np.sin(t)**3; y=-(13*np.cos(t)-5*np.cos(2*t)-2*np.cos(3*t)-np.cos(4*t))
    p=np.stack([x,y],1)*s/16
    c,sn=math.cos(rot),math.sin(rot); R=np.array([[c,-sn],[sn,c]])
    return (p@R.T+[cx,cy]).astype(np.float32)
def star_pts(cx,cy,s,rot=0):
    pts=[]
    for i in range(10):
        r=s if i%2==0 else s*.45; a=rot+i*math.pi/5-math.pi/2
        pts.append((cx+r*math.cos(a),cy+r*math.sin(a)))
    return np.array(pts,np.float32)

# ---------------- sprites chữ ----------------
def glow_text(text,size,fill,stroke,glow,pad=40):
    f=ImageFont.truetype(FB,size); tmp=Image.new("RGBA",(10,10)); d=ImageDraw.Draw(tmp)
    bb=d.textbbox((0,0),text,font=f,stroke_width=8); w,h=bb[2]-bb[0]+2*pad,bb[3]-bb[1]+2*pad
    base=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(base)
    d.text((pad-bb[0],pad-bb[1]),text,font=f,fill=glow+(255,),stroke_width=10,stroke_fill=glow+(255,))
    g=base.filter(ImageFilter.GaussianBlur(14)); out=Image.new("RGBA",(w,h),(0,0,0,0)); out.alpha_composite(g); out.alpha_composite(g)
    d=ImageDraw.Draw(out)
    d.text((pad-bb[0],pad-bb[1]+4),text,font=f,fill=stroke+(255,),stroke_width=7,stroke_fill=stroke+(255,))
    d.text((pad-bb[0],pad-bb[1]),text,font=f,fill=fill+(255,),stroke_width=0)
    return np.array(out)
def pill(text,size=40):
    f=ImageFont.truetype(FB,size); d=ImageDraw.Draw(Image.new("RGBA",(10,10))); bb=d.textbbox((0,0),text,font=f)
    tw,th=bb[2]-bb[0],bb[3]-bb[1]; hp=size*0.9; w=int(tw+size*4.4); h=int(th+size*1.2); pad=30
    im=Image.new("RGBA",(w+2*pad,h+2*pad),(0,0,0,0)); sh=Image.new("RGBA",im.size,(0,0,0,0))
    ImageDraw.Draw(sh).rounded_rectangle((pad,pad+6,pad+w,pad+h+6),radius=h//2,fill=(255,105,180,170))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d=ImageDraw.Draw(im); d.rounded_rectangle((pad,pad,pad+w,pad+h),radius=h//2,fill=(255,255,255,240))
    d.text((pad+(w-tw)/2-bb[0],pad+(h-th)/2-bb[1]-1),text,font=f,fill=(194,24,91,255))
    a=np.array(im)
    for sx in (pad+h*0.7,pad+w-h*0.7):   # tim nhỏ hai bên
        pts=heart_pts(sx,pad+h/2,size*0.55).astype(np.int32); cv2.fillPoly(a,[pts],(255,95,168,255),cv2.LINE_AA)
    return a
def ease_back(t,s=1.9):
    t=min(max(t,0),1)-1; return t*t*((s+1)*t+s)+1
def blit(frame,spr,cx,cy,scale,alpha):
    if alpha<=0.003 or scale<=0.01: return
    h,w=spr.shape[:2]; nw,nh=max(2,int(w*scale)),max(2,int(h*scale))
    s=cv2.resize(spr,(nw,nh),interpolation=cv2.INTER_LINEAR if scale>=1 else cv2.INTER_AREA)
    x0,y0=int(cx-nw/2),int(cy-nh/2); x1,y1=x0+nw,y0+nh
    sx0,sy0=max(0,-x0),max(0,-y0); x0,y0=max(0,x0),max(0,y0); x1,y1=min(W,x1),min(H,y1)
    if x1<=x0 or y1<=y0: return
    s=s[sy0:sy0+(y1-y0),sx0:sx0+(x1-x0)]
    a=(s[...,3:4].astype(np.float32)/255)*alpha
    roi=frame[y0:y1,x0:x1].astype(np.float32); frame[y0:y1,x0:x1]=(roi*(1-a)+s[...,:3]*a).astype(np.uint8)

TITLE=glow_text(f"Chúc Mừng Sinh Nhật!",78,(255,255,255),(255,79,154),(255,95,168))
TITLE2=glow_text(f"Chúc Mừng Sinh Nhật {NAME}!",66,(255,255,255),(255,79,154),(255,95,168))
PILLS=[pill(w) for w in WISHES]
# lịch chữ: (t0,t1,sprite,cy)
SCHED=[(PARTY+.7,PARTY+4.3,TITLE,78)]
t=PARTY+4.5
for p in PILLS: SCHED.append((t,t+2.5,p,82)); t+=2.6
SCHED.append((t+.1,DUR,TITLE2,78))

# ---------------- pháo hoa ----------------
bursts=[]; t=PARTY+.15
while t<DUR-.8:
    reg=random.choice([0,1]); cx=random.uniform(90,400) if reg==0 else random.uniform(880,1190); cy=random.uniform(90,230)
    bursts.append(dict(f=int(t*FPS),cx=cx,cy=cy,kind=random.choice(["ring","ring","heart","ball"]),col=random.choice(COL[:6])))
    t+=random.uniform(.45,.85)
rockets=[]; parts=[]
def launch(b):
    rockets.append(dict(x=b["cx"]+random.uniform(-30,30),y=H*.55,tx=b["cx"],ty=b["cy"],b=b,n=0,N=13))
def explode(b):
    cx,cy,k,c=b["cx"],b["cy"],b["kind"],b["col"]; c2=random.choice(COL[:6])
    if k=="heart":
        for p in heart_pts(0,0,1.0,n=70):
            vx,vy=p[0]*7.0,p[1]*7.0-.4; parts.append(dict(x=cx,y=cy,vx=vx,vy=vy,life=0,L=random.randint(34,46),c=c,g=.07,d=.955))
    else:
        n=95
        for i in range(n):
            a=random.uniform(0,6.283) if k=="ball" else i/n*6.283
            sp=random.uniform(2,9.5) if k=="ball" else 8.2+random.uniform(-.3,.3)
            parts.append(dict(x=cx,y=cy,vx=math.cos(a)*sp,vy=math.sin(a)*sp,life=0,L=random.randint(36,54),c=c if i%3 else c2,g=.09,d=.955))
    for i in range(14): parts.append(dict(x=cx,y=cy,vx=random.uniform(-1,1),vy=random.uniform(-1,1),life=0,L=14,c=(255,255,255),g=0,d=.9))
for b in bursts: b["lf"]=b["f"]-13
# ---------------- giấy pháo ----------------
conf=[]
def newc(burst=False):
    kind=random.choices(["rect","heart","star","dot"],[.55,.2,.12,.13])[0]
    conf.append(dict(x=random.uniform(0,W),y=(-random.uniform(0,H*.9) if burst else -20),vx=random.uniform(-1.2,1.2),vy=random.uniform(4,9),
      r=random.uniform(0,6.28),vr=random.uniform(-.2,.2),s=random.uniform(5,9.5),c=random.choice(COL),ph=random.uniform(0,6.28),vp=random.uniform(.12,.3),k=kind,wob=random.uniform(0,6.28)))
def draw_conf(fr):
    keep=[]
    for p in conf:
        p["y"]+=p["vy"]; p["wob"]+=.06; p["x"]+=p["vx"]+math.sin(p["wob"])*1.1; p["r"]+=p["vr"]; p["ph"]+=p["vp"]
        if p["y"]>H+30: continue
        keep.append(p); fl=abs(math.cos(p["ph"])); sh=.6+.4*fl; col=tuple(int(v*sh) for v in p["c"]); s=p["s"]
        if p["k"]=="rect":
            w,h=s*max(fl,.18),s*.55; c,sn=math.cos(p["r"]),math.sin(p["r"])
            pts=np.array([[-w,-h],[w,-h],[w,h],[-w,h]],np.float32); R=np.array([[c,-sn],[sn,c]],np.float32)
            cv2.fillConvexPoly(fr,((pts@R.T)+[p["x"],p["y"]]).astype(np.int32),col,cv2.LINE_AA)
        elif p["k"]=="heart": cv2.fillPoly(fr,[heart_pts(p["x"],p["y"],s*1.5,p["r"]*.3).astype(np.int32)],col,cv2.LINE_AA)
        elif p["k"]=="star": cv2.fillPoly(fr,[star_pts(p["x"],p["y"],s*1.1,p["r"]).astype(np.int32)],col,cv2.LINE_AA)
        else: cv2.circle(fr,(int(p["x"]),int(p["y"])),int(s*.45),col,-1,cv2.LINE_AA)
    conf[:]=keep

# ---------------- lấp lánh góc trên ----------------
TW=[(random.uniform(40,1240),random.uniform(20,330),random.uniform(0,6.28),random.uniform(.05,.12),random.uniform(5,11)) for _ in range(18)]

buf=np.zeros((H,W,3),np.float32)
def fx_frame(fi,fr):
    t=fi/FPS; global buf
    buf*=.84
    # lấp lánh nhẹ (sau khi tiệc bắt đầu)
    if t>=PARTY-.3:
        for (x,y,ph,sp,sz) in TW:
            a=max(0,math.sin(ph+fi*sp*2))**3
            if a>.05:
                cv2.fillPoly(buf,[star_pts(x,y,sz*(.5+a),0).astype(np.int32)],tuple(float(a) for _ in range(3)),cv2.LINE_AA)
    for b in bursts:
        if b["lf"]==fi: launch(b)
        if b["f"]==fi: explode(b)
    for r in rockets[:]:
        r["n"]+=1; k=r["n"]/r["N"]; r["x"]+=(r["tx"]-r["x"])*.18; r["y"]=H*.55+(r["ty"]-H*.55)*(1-(1-k)**2)
        cv2.circle(buf,(int(r["x"]),int(r["y"])),3,(1,.85,.55),-1,cv2.LINE_AA)
        if r["n"]>=r["N"]: rockets.remove(r)
    for p in parts[:]:
        p["life"]+=1; p["vx"]*=p["d"]; p["vy"]=p["vy"]*p["d"]+p["g"]; p["x"]+=p["vx"]; p["y"]+=p["vy"]
        if p["life"]>p["L"]: parts.remove(p); continue
        a=min(1,1.5*(1-p["life"]/p["L"])**.6)*(0.8+0.2*random.random()); c=[v/255*a for v in p["c"]]
        cv2.circle(buf,(int(p["x"]),int(p["y"])),3,c,-1,cv2.LINE_AA)
    glow=cv2.GaussianBlur(buf,(0,0),9)
    fw=np.clip(buf*1.1+glow*2.4,0,1)
    f=fr.astype(np.float32)/255; out=1-(1-f)*(1-fw*.95)
    fr[:]=(out*255).astype(np.uint8)
    # giấy pháo
    if t>=PARTY:
        if fi==int(PARTY*FPS):
            for _ in range(85): newc(True)
        elif t<DUR-3.2:
            
            if random.random()<.7: newc()
    draw_conf(fr)
    # chữ
    for (t0,t1,spr,cy) in SCHED:
        if t0<=t<t1:
            ti,to=t-t0,t1-t
            sc=ease_back(ti/.4); al=min(1,ti/.2)*min(1,to/.35) if t1<DUR else min(1,ti/.2)
            if spr is TITLE or spr is TITLE2:
                if spr is TITLE2 and t1>=DUR: sc=ease_back(ti/.5)
            bob=math.sin(t*3)*3
            blit(fr,spr,W/2,cy+bob-(1-min(1,to/.35))*14 if t1<DUR else cy+bob,sc*(0.98 if spr is TITLE2 else 1),al)

MIX='_mix.wav'
def build_audio():
    import numpy as np
    SR=44100; START=(ARGS.song if ARGS.song is not None else ARGS.party-.1); b=0.45
    N={'G4':392,'A4':440,'B4':493.88,'C5':523.25,'D5':587.33,'E5':659.25,'F5':698.46,'G5':783.99}
    m=[['G4',.75],['G4',.25],['A4',1],['G4',1],['C5',1],['B4',2],['G4',.75],['G4',.25],['A4',1],['G4',1],['D5',1],['C5',2],['G4',.75],['G4',.25],['G5',1],['E5',1],['C5',1],['B4',1],['A4',2],['F5',.75],['F5',.25],['E5',1],['C5',1],['D5',1],['C5',3]]
    out=np.zeros(int(SR*DUR)+SR)
    t=START
    for rep in range(2):
        for n,d in m:
            L=d*b; i0=int(t*SR); dur=L+0.5; k=int(dur*SR); x=np.arange(k)/SR
            f=N[n]
            # nốt kiểu đàn hộp nhạc/glockenspiel: sine + hài bậc 2,3 + tắt dần
            w=np.sin(2*np.pi*f*x)+.45*np.sin(2*np.pi*2*f*x)*np.exp(-x*6)+.2*np.sin(2*np.pi*3*f*x)*np.exp(-x*9)+.25*np.sin(2*np.pi*.5*f*x)
            env=np.minimum(1,x/.008)*np.exp(-x*(3.2 if d<2 else 2.2))
            v=w*env
            # hòa âm thấp nhẹ trên nốt dài
            out[i0:i0+k]+=v[:max(0,len(out)-i0)]*0.5
            t+=L
    out=out[:int(SR*DUR)]
    # reverb nhẹ
    ir=np.exp(-np.arange(int(SR*.35))/SR*9)*np.random.RandomState(1).randn(int(SR*.35))*.08; ir[0]=1
    rev=np.convolve(out,ir)[:len(out)]
    out=out*.7+rev*.5
    # fade vào/ra
    fo=int(SR*.6); out[-fo:]*=np.linspace(1,0,fo)
    # chuẩn hoá mức: RMS phần có nhạc ~ -17 dB
    act=out[int(START*SR):]; rms=np.sqrt(np.mean(act**2)); out*=10**(-17/20)/rms
    out=np.clip(out,-.95,.95)
    st=np.stack([out,out],1)
    pcm=(st*32767).astype(np.int16)
    with wave.open("_song.wav","wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    has_a=bool(subprocess.run(["ffprobe","-v","error","-select_streams","a","-show_entries","stream=index","-of","csv=p=0",V],capture_output=True,text=True).stdout.strip())
    if not has_a: subprocess.run(["ffmpeg","-v","error","-y","-i","_song.wav","-ac","2",MIX],check=True); return
    subprocess.run(["ffmpeg","-v","error","-y","-i",V,"-i","_song.wav","-filter_complex","[0:a]aresample=44100,volume=0.9[a];[1:a]volume=1.0[b];[a][b]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[m]","-map","[m]","-ac","2",MIX],check=True)

def main():
    rd=subprocess.Popen(["ffmpeg","-v","error","-i",V,"-vf","scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24","-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
    wr=None
    if not PREVIEW:
        build_audio()
        wr=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-i",MIX,
            "-map","0:v","-map","1:a","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart","-shortest",ARGS.output],stdin=subprocess.PIPE)
    prev={int(t*FPS) for t in PREV_T}
    for fi in range(NF):
        raw=rd.stdout.read(W*H*3)
        if len(raw)<W*H*3: break
        fr=np.frombuffer(raw,np.uint8).reshape(H,W,3).copy()
        fx_frame(fi,fr)
        if PREVIEW and fi in prev: Image.fromarray(fr).save(f"prev_{fi/FPS:05.2f}.png")
        if wr: wr.stdin.write(fr.tobytes())
    if wr: wr.stdin.close(); wr.wait()
    rd.stdout.close(); rd.wait()
if __name__=="__main__": main()
