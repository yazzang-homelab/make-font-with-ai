"""Actual FreeType output, including exact 1x pixel-grid comparisons."""
from __future__ import annotations
import io
import math
from pathlib import Path
import numpy as np
import freetype
import uharfbuzz as hb
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from .common import require, sha, write_json
from .brief import characters

class Renderer:
    def __init__(self,data:bytes,b:dict):
        self.font=TTFont(io.BytesIO(data));self.face=freetype.Face(io.BytesIO(data))
        self.b=b;self.cmap=self.font.getBestCmap();self.upm=self.font['head'].unitsPerEm
    def glyph(self,c:str,size:int):
        name=self.cmap.get(ord(c));require(name is not None,'MISSING_GLYPH',repr(c))
        self.face.set_pixel_sizes(0,size)
        flags=freetype.FT_LOAD_RENDER|freetype.FT_LOAD_NO_HINTING|freetype.FT_LOAD_NO_AUTOHINT
        if not self.b['target']['antialiasing']:flags|=freetype.FT_LOAD_TARGET_MONO|freetype.FT_LOAD_MONOCHROME
        self.face.load_glyph(self.font.getGlyphID(name),flags)
        slot=self.face.glyph;bm=slot.bitmap;m=self.b['metrics']
        width=max(1,round(self.font['hmtx'][name][0]*size/self.upm))
        height=math.ceil((m['ascent']-m['descent'])*size/self.upm)
        require(width*height<=16_000_000,'RASTER_BUDGET','A single glyph canvas exceeds 16 million pixels')
        a=np.zeros((height,width),np.uint8)
        if not bm.rows or not bm.width:return a,False
        raw=np.asarray(bm.buffer,dtype=np.uint8).reshape(bm.rows,abs(bm.pitch))
        if bm.pixel_mode==freetype.FT_PIXEL_MODE_MONO:ink=np.unpackbits(raw,axis=1)[:,:bm.width]*255
        else:ink=raw[:,:bm.width]
        x=slot.bitmap_left;y=round(m['ascent']*size/self.upm)-slot.bitmap_top
        clipped=x<0 or y<0 or x+bm.width>width or y+bm.rows>height
        # Keep a proof even for a rejected candidate, but never call clipping a pass.
        x0=max(0,x);y0=max(0,y);x1=min(width,x+bm.width);y1=min(height,y+bm.rows)
        if x1>x0 and y1>y0:a[y0:y1,x0:x1]=ink[y0-y:y1-y,x0-x:x1-x]
        return a,clipped

def shape(data,text,upm):
    f=hb.Font(hb.Face(data));f.scale=(upm,upm);hb.ot_font_set_funcs(f)
    b=hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(f,b)
    return [[i.codepoint,p.x_advance,p.y_advance,p.x_offset,p.y_offset]
            for i,p in zip(b.glyph_infos,b.glyph_positions)]

def verify(data:bytes,b:dict,source:dict,meta:dict) -> dict:
    import unicodedata
    r=Renderer(data,b);f=r.font;chars=characters(b);fail=[];records=[];sizes=b['target']['sizes_px']
    def bad(code,char=None,size=None,detail=None):
        fail.append({'code':code,'char':char,'size':size,'detail':detail})
    for c in chars:
        name=r.cmap.get(ord(c))
        if name is None:bad('MISSING_GLYPH',c);continue
        gl=f['glyf'][name];gl.recalcBounds(f['glyf'])
        if not c.isspace() and gl.numberOfContours==0:bad('EMPTY_GLYPH',c)
        advance=f['hmtx'][name][0]
        if b['metrics']['spacing']=='monospace' and advance!=b['metrics']['advance']:bad('WRONG_ADVANCE',c)
        if gl.numberOfContours:
            if gl.xMin<0 or gl.xMax>advance or gl.yMin<b['metrics']['descent'] or gl.yMax>b['metrics']['ascent']:
                bad('GLYPH_BOUNDS',c,detail=[gl.xMin,gl.yMin,gl.xMax,gl.yMax])
        nfc=unicodedata.normalize('NFC',c);nfd=unicodedata.normalize('NFD',c)
        a=shape(data,nfc,r.upm);bb=shape(data,nfd,r.upm)
        if a!=bb or any(x[0]==0 for x in a):bad('NFC_NFD_SHAPING',c)
    collisions=0;pixel_cases=0;center_max=0.
    for size in sizes:
        hashes={};masks={}
        for c in chars:
            if ord(c) not in r.cmap:continue
            a,clipped=r.glyph(c,size);masks[c]=a
            if clipped:bad('RASTER_CLIPPED',c,size)
            if not c.isspace() and not a.any():bad('RASTER_EMPTY',c,size)
            h=sha(str(a.shape).encode()+a.tobytes())
            if not c.isspace() and h in hashes:
                collisions+=1;bad('DUPLICATE_VISIBLE_GLYPH',c,size,hashes[h])
            elif not c.isspace():hashes[h]=c
            if b['production_kind']=='bitmap':
                grid=source['glyphs'][c]['pixels'];scale=size//b['target']['native_cell_px'][1]
                expected=np.array([[255 if x in '#1' else 0 for x in row] for row in grid],dtype=np.uint8)
                expected=np.repeat(np.repeat(expected,scale,axis=0),scale,axis=1);pixel_cases+=1
                if a.shape!=expected.shape or not np.array_equal(a,expected):bad('NATIVE_PIXEL_MISMATCH',c,size)
            if a.any() and not c.isspace():
                ys,xs=np.nonzero(a>96)
                if len(xs):
                    # Blend mass and core bounds, leaving intentional calligraphic asymmetry.
                    lo,hi=np.quantile(xs,[.02,.98]);center=.52*(xs.mean()+.5)+.48*((lo+hi)/2+.5)
                    error=abs(center-a.shape[1]/2)/size;center_max=max(center_max,float(error))
                    if error>b['acceptance']['max_center_offset_em']:bad('OPTICAL_CENTER_FLAG',c,size,round(float(error),5))
            records.append({'char':c,'codepoint':f'U+{ord(c):04X}','size':size,'raster_sha256':h})
        for pair in b['acceptance']['critical_pairs']:
            if pair[0] in masks and pair[1] in masks and np.array_equal(masks[pair[0]],masks[pair[1]]):
                bad('CRITICAL_PAIR_COLLAPSED',pair,size)
    # Specialized profile tests come from the actual R36 engine run, not a constant true label.
    if meta.get('engine')=='r36-hangul':
        special=meta.get('specialized_checks')
        if not isinstance(special,dict) or not special or not all(v is True for v in special.values()):
            bad('R36_PROFILE_GATES',detail=special)
    return {'pass':not fail,'font_raw_sha256':sha(data),'character_count':len(chars),
            'raster_cases':len(records),'native_pixel_equality_cases':pixel_cases,
            'normalization_cases':len(chars),'visible_collisions':collisions,
            'max_center_error_em':round(center_max,6),'failures':fail,
            'raster_records':records,'specialized_checks':meta.get('specialized_checks'),
            'target_engine_tested':False,'artistic_reference_equivalence':False}

def proofs(data:bytes,b:dict,out:Path) -> list[dict]:
    out.mkdir(parents=True,exist_ok=True);r=Renderer(data,b);chars=characters(b);entries=[]
    label=ImageFont.load_default(size=14)
    for size in b['target']['sizes_px']:
        # Bitmap 1x remains truly 1x in its own proof. Enlargement is a separate file.
        width=max(96,math.ceil(b['metrics']['advance']*size/r.upm)+18)
        height=math.ceil((b['metrics']['ascent']-b['metrics']['descent'])*size/r.upm)+36
        cols=max(1,min(10,1800//width));count=cols*10
        for page,start in enumerate(range(0,len(chars),count),1):
            text=chars[start:start+count];im=Image.new('RGB',(cols*width,math.ceil(len(text)/cols)*height+35),'#141718')
            draw=ImageDraw.Draw(im);draw.text((8,7),f'{size}px / page {page} / actual FreeType output',font=label,fill='#b4c0c3')
            for i,c in enumerate(text):
                x=(i%cols)*width;y=(i//cols)*height+35
                draw.text((x+7,y+2),f'U+{ord(c):04X}',font=label,fill='#b4c0c3')
                a,_=r.glyph(c,size);mask=Image.fromarray(a)
                im.paste('#f4eedc',(x+(width-mask.width)//2,y+23),mask)
            name=f'size{size:03d}-page{page:03d}.png';im.save(out/name)
            entries.append({'file':name,'size_px':size,'characters':text,'sha256':sha((out/name).read_bytes()),'kind':'glyphs'})
    for size in b['target']['sizes_px']:
        lines=b['acceptance']['specimen_text'].splitlines();can=[]
        space=round(b['metrics']['advance']*size/r.upm)
        for line in lines:
            aa=[]
            for c in line:
                if c==' ' and c not in r.cmap:aa.append(np.zeros((math.ceil((b['metrics']['ascent']-b['metrics']['descent'])*size/r.upm),space),np.uint8))
                else:aa.append(r.glyph(c,size)[0])
            can.append(aa)
        ww=max([sum(a.shape[1] for a in line) for line in can]+[1]);hh=sum(max([a.shape[0] for a in line]+[size])+8 for line in can)
        require(ww<=12000 and hh<=12000,'SPECIMEN_TOO_LARGE','Split specimen text into shorter lines')
        im=Image.new('RGB',(ww+20,hh+20),'#141718');y=10
        for line in can:
            x=10
            for a in line:im.paste('#f4eedc',(x,y),Image.fromarray(a));x+=a.shape[1]
            y+=max([a.shape[0] for a in line]+[size])+8
        name=f'specimen-{size:03d}px.png';im.save(out/name)
        entries.append({'file':name,'size_px':size,'sha256':sha((out/name).read_bytes()),'kind':'specimen'})
        if b['production_kind']=='bitmap' and size==b['target']['native_cell_px'][1]:
            name=f'specimen-{size:03d}px-nearest4x.png'
            im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST).save(out/name)
            entries.append({'file':name,'size_px':size,'sha256':sha((out/name).read_bytes()),'kind':'inspection_enlargement'})
    write_json(out/'pages.json',entries)
    import html
    document='<!doctype html><meta charset="utf-8"><title>Actual font proof</title><style>body{background:#141718;color:#eee;font:16px system-ui}img{display:block;max-width:100%;margin:20px 0}code{overflow-wrap:anywhere}</style><h1>Actual compiled font proof</h1><p>Review glyph identity, reference style, spacing, and native-size readability. This page is not automatic visual approval.</p>'
    for entry in entries:
        document+=f'<h2>{html.escape(entry["file"])}</h2><img loading="lazy" src="{entry["file"]}" alt="actual font"><code>{entry["sha256"]}</code>'
    (out/'index.html').write_text(document,encoding='utf-8')
    return entries

def atlas(data:bytes,b:dict,out:Path) -> dict:
    size=b['target']['sizes_px'][0];r=Renderer(data,b);chars=characters(b)
    images=[r.glyph(c,size)[0] for c in chars]
    cw=max(a.shape[1] for a in images)+2;ch=max(a.shape[0] for a in images)+2
    cols=max(1,min(32,4096//cw));rows=max(1,4096//ch);capacity=cols*rows;mapping={};pages=[]
    out.mkdir(parents=True,exist_ok=True)
    for start in range(0,len(chars),capacity):
        im=Image.new('L',(cols*cw,min(rows,math.ceil((len(chars)-start)/cols))*ch));number=len(pages)
        for i,c in enumerate(chars[start:start+capacity]):
            a=images[start+i];x=(i%cols)*cw+1;y=(i//cols)*ch+1;im.paste(Image.fromarray(a),(x,y))
            mapping[c]={'page':number,'rect':[x,y,a.shape[1],a.shape[0]],'advance_px':a.shape[1]}
        name=f'atlas-{number:03d}.png';im.save(out/name);pages.append({'file':name,'sha256':sha((out/name).read_bytes())})
    result={'size_px':size,'pages':pages,'codepoint_order':list(chars),'glyphs':mapping,
            'baseline_px':round(b['metrics']['ascent']*size/r.upm),'target_engine_tested':False}
    write_json(out/'atlas.json',result);return result
