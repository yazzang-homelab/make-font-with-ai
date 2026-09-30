"""Build reviewed drawing data, not guessed glyphs, into a real TrueType font."""
from __future__ import annotations
import io
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont, newTable
from .common import require, GateError, read_json, safe_path, digest, sha, engine_signature
from .brief import characters, brief_identity

MAX_POINTS = 32000

def source_data(root:Path,b:dict) -> dict:
    if b['source']['kind']=='r36-hangul':
        # This particular reference engine is NOT a universal image-to-font model.
        require(b['font']['upm']==1000 and b['metrics']=={
            'ascent':1040,'descent':-200,'line_gap':0,'advance':1000,'spacing':'monospace'},
            'R36_METRICS', 'R36 must retain its reviewed metric envelope')
        require(all(0xAC00<=ord(c)<=0xD7A3 or c==' ' for c in characters(b)),
                'R36_COVERAGE','This profile currently exports modern Hangul and space')
        return {'kind':'r36-hangul','profile_version':'0.636'}
    return read_json(safe_path(root,b['source'].get('path')))

def input_identity(root:Path,b:dict) -> str:
    return digest({'brief':brief_identity(root,b),'drawings':source_data(root,b),
                   'engine':engine_signature()})

def _polygon(pen,points,ascent,*,hole=False):
    require(isinstance(points,list) and 3<=len(points)<=MAX_POINTS,'CONTOUR_SIZE','Invalid contour')
    out=[]
    for p in points:
        require(isinstance(p,list) and len(p)==2 and all(type(x) in (int,float) and math.isfinite(x)
                and abs(x)<32000 for x in p),'COORDINATE','Invalid drawing coordinate')
        xy=(round(p[0]),round(ascent-p[1]))
        if not out or xy!=out[-1]:out.append(xy)
    if len(out)>1 and out[0]==out[-1]:out.pop()
    require(len(set(out))>=3,'EMPTY_CONTOUR','Contour collapsed after rounding')
    area=sum(x1*y2-x2*y1 for (x1,y1),(x2,y2) in zip(out,out[1:]+out[:1]))
    require(area!=0,'ZERO_AREA_CONTOUR','Degenerate polygon')
    # TrueType exterior clockwise, hole counterclockwise.
    if (area>0) != hole:out.reverse()
    pen.moveTo(out[0])
    for xy in out[1:]:pen.lineTo(xy)
    pen.closePath()

def make_font(b:dict,source:dict) -> tuple[TTFont,dict]:
    text=characters(b);upm=b['font']['upm'];asc=b['metrics']['ascent'];meta={}
    require(source.get('format') in ('bitmap-v1','vector-v1'),'DRAWING_FORMAT','Invalid source format')
    drawings=source.get('glyphs');require(isinstance(drawings,dict),'DRAWINGS','Expected glyph map')
    require(set(drawings)==set(text),'DRAWING_COVERAGE','Source glyphs must exactly match approved coverage')
    bitmap=b['production_kind']=='bitmap'
    require(source['format']==('bitmap-v1' if bitmap else 'vector-v1'),'DRAWING_KIND','Source kind mismatch')
    glyphs={};metrics={};cmap={}
    nd=TTGlyphPen(None)
    _polygon(nd,[[upm*.1,upm*.1],[upm*.85,upm*.1],[upm*.85,upm*.9],[upm*.1,upm*.9]],asc)
    glyphs['.notdef']=nd.glyph();metrics['.notdef']=(b['metrics']['advance'],0)
    cell=b['target']['native_cell_px'];scale=upm/cell[1] if bitmap else 1
    for c in sorted(text,key=ord):
        g=drawings[c];require(isinstance(g,dict),'GLYPH_RECORD',repr(c))
        advance=g.get('advance',b['metrics']['advance'])
        require(type(advance)is int and 0<advance<32000,'ADVANCE',repr(c))
        if b['metrics']['spacing']=='monospace':require(advance==b['metrics']['advance'],'MONOSPACE',repr(c))
        pen=TTGlyphPen(None)
        if bitmap:
            pixels=g.get('pixels')
            require(isinstance(pixels,list) and len(pixels)==cell[1] and all(isinstance(r,str) and
                len(r)==cell[0] and set(r)<=set('.#01') for r in pixels),'PIXEL_GRID',repr(c))
            for y,row in enumerate(pixels):
                x=0
                while x<len(row):
                    if row[x] not in '#1':x+=1;continue
                    end=x+1
                    while end<len(row) and row[end] in '#1':end+=1
                    _polygon(pen,[[x*scale,y*scale],[end*scale,y*scale],
                                  [end*scale,(y+1)*scale],[x*scale,(y+1)*scale]],asc)
                    x=end
        else:
            require(set(g)<= {'advance','contours','svg_path'},'GLYPH_FIELD',repr(c))
            if 'svg_path' in g:
                path=g['svg_path'];require(isinstance(path,str) and 0<len(path)<=300000,'SVG_PATH','Invalid path data')
                try:
                    parse_path(path,TransformPen(Cu2QuPen(pen,max_err=.35), (1,0,0,-1,0,asc)))
                except Exception as e:raise GateError('SVG_PATH_PARSE',repr(c)+': '+str(e)) from e
            else:
                contours=g.get('contours');require(isinstance(contours,list) and len(contours)<=8192,'CONTOURS',repr(c))
                for contour in contours:
                    require(isinstance(contour,dict) and set(contour)<={'points','hole'},'CONTOUR',repr(c))
                    require(type(contour.get('hole',False))is bool,'CONTOUR_HOLE',repr(c))
                    _polygon(pen,contour.get('points'),asc,hole=contour.get('hole',False))
        gl=pen.glyph();name=f'u{ord(c):06X}';glyphs[name]=gl;cmap[ord(c)]=name
        gl.recalcBounds(glyphs)
        require(len(getattr(gl,'coordinates',[]))<=MAX_POINTS,'POINT_LIMIT',repr(c))
        require(c.isspace() or gl.numberOfContours>0,'EMPTY_GLYPH',repr(c))
        metrics[name]=(advance,getattr(gl,'xMin',0))
        meta[c]={'advance':advance}
    fb=FontBuilder(upm,isTTF=True);fb.setupGlyphOrder(list(glyphs));fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs);fb.setupHorizontalMetrics(metrics)
    m=b['metrics'];fb.setupHorizontalHeader(ascent=m['ascent'],descent=m['descent'],lineGap=m['line_gap'])
    setup_names(fb,b)
    fb.setupOS2(sTypoAscender=m['ascent'],sTypoDescender=m['descent'],sTypoLineGap=m['line_gap'],
                usWinAscent=m['ascent'],usWinDescent=-m['descent'],fsType=0,fsSelection=0xC0,version=4)
    fb.setupPost();fb.setupMaxp()
    if bitmap:
        gasp=newTable('gasp');gasp.gaspRange={65535:0};fb.font['gasp']=gasp
    fb.font['head'].created=fb.font['head'].modified=3786912000
    fb.font.recalcTimestamp=False
    return fb.font,{'engine':'generic','glyphs':meta}

def setup_names(fb,b):
    family=b['font']['family'];version=b['font']['version']
    ps=re.sub('[^A-Za-z0-9-]','',family)[:46] or 'AIFont'
    ps+='-'+digest(family)[:8]
    fb.setupNameTable({'familyName':family,'styleName':'Regular','fullName':family+' Regular',
        'psName':ps+'-Regular','version':'Version '+version,'uniqueFontIdentifier':ps+'-'+version,
        'description':'Reference-driven font. Check the accompanying review and rights records.'})

def compile_font(root:Path,b:dict) -> tuple[bytes,dict,dict]:
    src=source_data(root,b)
    if b['source']['kind']=='r36-hangul':
        engine=Path(__file__).parent/'engines/hangul_brush'
        require((engine/'worker.py').is_file(),'ENGINE_MISSING','Install from the complete repository')
        with tempfile.TemporaryDirectory(prefix='mfai-brush-') as tmp:
            config=Path(tmp)/'job.json';config.write_text(json.dumps({'characters':characters(b)}))
            out=Path(tmp)/'candidate.ttf';manifest=Path(tmp)/'manifest.json'
            p=subprocess.run([sys.executable,str(engine/'worker.py'),str(config),str(out),str(manifest)],
                             capture_output=True,text=True,timeout=1800)
            require(p.returncode==0,'BRUSH_ENGINE',p.stderr[-4000:] or p.stdout[-4000:])
            data=out.read_bytes();meta=read_json(manifest)
        f=TTFont(io.BytesIO(data));f.recalcTimestamp=False
        # Rename only the name table; never rescale reviewed component outlines.
        fb=FontBuilder(font=f);setup_names(fb,b);stream=io.BytesIO();f.save(stream);data=stream.getvalue()
    else:
        f,meta=make_font(b,src);stream=io.BytesIO();f.save(stream);data=stream.getvalue()
    require(len(data)<=b['acceptance']['max_font_bytes'],'FONT_TOO_LARGE',str(len(data)))
    TTFont(io.BytesIO(data))
    return data,meta,src
