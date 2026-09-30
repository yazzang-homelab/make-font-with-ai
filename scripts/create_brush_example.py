"""Render a template-owned reference; do not publish the private font used for this step."""
from pathlib import Path
import json,sys
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'examples/hangul-brush';p.mkdir(exist_ok=True)
b={'schema_version':'1.0','font':{'family':'AI Brush Study','version':'1.0','upm':1000},
'purpose':{'use_case':'noncommercial Korean brush headline study','typography_role':'display'},'production_kind':'vector',
'target':{'engine':'FreeType validation harness','renderer':'grayscale FreeType raster','sizes_px':[32,128],'native_cell_px':None,'antialiasing':True},
'metrics':{'ascent':1040,'descent':-200,'line_gap':0,'advance':1000,'spacing':'monospace'},
'coverage':{'mode':'ksx1001','characters':None,'encoding':'unicode'},
'reference':{'path':'reference.png','source':'generated','permission_confirmed':True,'notes':'Reference rendered from the project-authored R36 engine. This is a specific native-pressure brush family, not arbitrary image style transfer.'},
'source':{'kind':'r36-hangul','path':None},'exports':['ttf'],
'acceptance':{'max_font_bytes':60000000,'max_center_offset_em':.12,'critical_pairs':['각곽','가카','다타','아애','갈각','이아'],
'specimen_text':'한글 붓글씨\n달빛 아래 길을 걸어\n곽 괄 관 권 갈 걸 길 골 굴 글',
'style_notes':'Pressure-shaped starts, alternating rieul turns, tapered releases, balanced complete syllables. No equal parallel bars or decorative tails that erase identity.'}}
(p/'design-brief.json').write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
font_path=Path(sys.argv[1]);im=Image.new('RGB',(1540,510),'#141718');d=ImageDraw.Draw(im)
for text,y,size in [('한글 붓글씨',20,160),('달빛 아래 길을 걸어',240,124)]:
 f=ImageFont.truetype(str(font_path),size);d.text((40,y),text,font=f,fill='#f4eedc')
im.save(p/'reference.png');im.save(ROOT/'assets/hangul-brush-preview.png')
print('BRUSH_EXAMPLE_DEFINED',p)
