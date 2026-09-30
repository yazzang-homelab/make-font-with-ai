"""Explicit image mapping helpers. Never infer a character identity with OCR."""
from __future__ import annotations
from pathlib import Path
import numpy as np
from PIL import Image
from .brief import approved, characters
from .common import require, read_json, write_json, safe_path, sha


def init_project(root:Path,kind:str='bitmap',cell:int=16):
    require(not root.exists() or not any(root.iterdir()),'PROJECT_EXISTS','Choose an empty folder')
    require(kind in ('bitmap','vector'),'PRODUCTION_KIND',kind)
    require(type(cell)is int and 4<=cell<=128,'CELL','Use an integer cell from 4 to 128')
    root.mkdir(parents=True,exist_ok=True);pixel=kind=='bitmap';upm=cell*64 if pixel else 1000
    brief={'schema_version':'1.0','font':{'family':'Untitled Font','version':'1.0','upm':upm},
      'purpose':{'use_case':None,'typography_role':None},'production_kind':kind,
      'target':{'engine':None,'renderer':None,'sizes_px':[cell,cell*2] if pixel else [32,128],
                'native_cell_px':[cell,cell] if pixel else None,'antialiasing':not pixel},
      'metrics':{'ascent':(cell-2)*64 if pixel else 900,'descent':-128 if pixel else -100,
                 'line_gap':0,'advance':upm,'spacing':'monospace'},
      'coverage':{'mode':'custom','characters':None,'encoding':'unicode'},
      'reference':{'path':'reference.png','source':None,'permission_confirmed':False,'notes':None},
      'source':{'kind':'bitmap-json' if pixel else 'vector-json','path':'glyphs.json'},
      'exports':['ttf','atlas'] if pixel else ['ttf'],
      'acceptance':{'max_font_bytes':50000000,'max_center_offset_em':.22,'critical_pairs':[],
                    'specimen_text':None,'style_notes':None}}
    write_json(root/'design-brief.json',brief)
    write_json(root/'glyphs.json',{'format':'bitmap-v1' if pixel else 'vector-v1','glyphs':{}})
    (root/'INTERVIEW.md').write_text('''# Confirm before implementation
1. Where will this font be used (dialogue, UI, display, reading)?
2. What is its actual size? Is 16x16 a fixed cell or merely a visual style?
3. Which target engine/loader and which characters/encoding are required?
Resolve baseline, spacing, smoothing and required outputs. Defaults are proposals,
not answers. Record rights and reference provenance. Ask for explicit confirmation,
then run `mfai confirm-brief . --by "name"`.
''',encoding='utf-8')
    return brief


def mask_image(path:Path,threshold:int,invert:bool):
    require(type(threshold)is int and 0<=threshold<=255,'THRESHOLD','0..255')
    require(path.is_file() and path.stat().st_size<=30_000_000,'IMAGE_SIZE','Missing/oversized image')
    with Image.open(path) as im:
        require(im.format in ('PNG','JPEG','WEBP'),'IMAGE_FORMAT','Use PNG/JPEG/WEBP')
        require(im.width*im.height<=16_000_000,'IMAGE_SIZE','Image exceeds pixel limit')
        rgba=im.convert('RGBA');gray=np.array(rgba.convert('L'));alpha=np.array(rgba.getchannel('A'))
    # Invert acts on ink luminance, never turns transparent pixels into ink.
    mask=(gray<=threshold if invert else gray>=threshold)&(alpha>=128)
    return mask


def import_atlas(root:Path,image:Path,columns:int,threshold:int=128,invert:bool=False):
    b=approved(root);require(b['production_kind']=='bitmap','BITMAP_REQUIRED','Use trace-glyph for vector')
    require(type(columns)is int and columns>0,'COLUMNS','Positive column count required')
    chars=characters(b);w,h=b['target']['native_cell_px'];mask=mask_image(image,threshold,invert)
    rows=(len(chars)+columns-1)//columns
    require(mask.shape==(rows*h,columns*w),'ATLAS_DIMENSIONS',
            f'Expected {columns*w}x{rows*h}; no automatic resizing, padding, or guessed mapping')
    glyphs={}
    for i,c in enumerate(chars):
        x=(i%columns)*w;y=(i//columns)*h;tile=mask[y:y+h,x:x+w]
        glyphs[c]={'pixels':[''.join('#' if p else '.' for p in row) for row in tile]}
    out=safe_path(root,b['source']['path'],exists=False)
    source={'format':'bitmap-v1','glyphs':glyphs,'provenance':{'image_sha256':sha(image.read_bytes()),
             'mapping':'explicit approved character order, row-major','threshold':threshold,'invert':invert}}
    write_json(out,source);return {'glyphs_imported':len(glyphs),'source':str(out),'resized':False}


def trace_glyph(root:Path,image:Path,char:str,threshold:int=128,invert:bool=False,box=None):
    b=approved(root);require(b['source']['kind']=='vector-json','VECTOR_REQUIRED','Only vector-json receives traced contours')
    require(len(char)==1 and char in characters(b),'CHAR_MAPPING','Select one declared character explicitly')
    mask=mask_image(image,threshold,invert)
    if box is not None:
        require(len(box)==4 and all(type(x)is int for x in box),'CROP','Use x y width height')
        x,y,w,h=box;require(x>=0 and y>=0 and w>0 and h>0 and x+w<=mask.shape[1] and y+h<=mask.shape[0],
                          'CROP_BOUNDS','Crop is outside the image')
        mask=mask[y:y+h,x:x+w]
    require(mask.any() and mask.shape[0]<=2048 and mask.shape[1]<=2048,'TRACE_SIZE','Crop one visible glyph <=2048px')
    try:from skimage.measure import find_contours, approximate_polygon
    except ImportError as exc:raise RuntimeError('Install the trace extra: pip install -e ".[trace]"') from exc
    curves=find_contours(np.pad(mask.astype(float),1),.5,fully_connected='low',positive_orientation='low')
    contours=[];H,W=mask.shape;upm=b['font']['upm']
    for c in curves:
        c=approximate_polygon(c,tolerance=.15)
        pts=[[float((x-1+.5)/W*upm),float((y-1+.5)/H*upm)] for y,x in c[:-1]]
        if len(pts)<3:continue
        area=sum(a[0]*bb[1]-bb[0]*a[1] for a,bb in zip(pts,pts[1:]+pts[:1]))
        if abs(area)<.5:continue
        contours.append({'points':pts,'hole':area<0})
    path=safe_path(root,b['source']['path'],exists=False)
    source=read_json(path) if path.exists() else {'format':'vector-v1','glyphs':{}}
    source['glyphs'][char]={'contours':contours}
    write_json(path,source)
    return {'character':char,'contours':len(contours),'source':str(path),
            'warning':'Candidate tracing only. Contextual spacing, identity and reference fidelity require review.'}
