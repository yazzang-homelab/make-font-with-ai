"""Author-owned small fixtures; no downloaded font data or proprietary glyphs."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def brief(kind,chars):
    pixel=kind=='bitmap';upm=1024 if pixel else 1000
    return {'schema_version':'1.0','font':{'family':'Native Sixteen' if pixel else 'Vector Study','version':'1.0','upm':upm},
      'purpose':{'use_case':'noncommercial retro dialogue study' if pixel else 'noncommercial display lettering study','typography_role':'dialogue' if pixel else 'display'},
      'production_kind':kind,
      'target':{'engine':'FreeType test harness','renderer':'monochrome FreeType raster' if pixel else 'grayscale FreeType raster','sizes_px':[16,32] if pixel else [32,128],'native_cell_px':[16,16] if pixel else None,'antialiasing':not pixel},
      'metrics':{'ascent':896 if pixel else 900,'descent':-128 if pixel else -100,'line_gap':0,'advance':upm,'spacing':'monospace'},
      'coverage':{'mode':'custom','characters':chars,'encoding':'unicode'},
      'reference':{'path':'reference.png','source':'owned','permission_confirmed':True,'notes':'Author-owned geometric/pixel drawing fixture. Not a commercial-font design or a full Hangul pixel family.'},
      'source':{'kind':'bitmap-json' if pixel else 'vector-json','path':'glyphs.json'},
      'exports':['ttf','atlas'] if pixel else ['ttf'],
      'acceptance':{'max_font_bytes':3000000,'max_center_offset_em':.22,'critical_pairs':[],
                    'specimen_text':'A B C\n가 각 갈 곽\n이 출' if pixel else 'ABC\nCAB',
                    'style_notes':'Preserve native single-pixel turns and spacing' if pixel else 'Preserve clean geometric stroke contrast'}}

def main():
    folder=ROOT/'examples/pixel16';folder.mkdir(parents=True,exist_ok=True)
    patterns={'A':['01110','10001','10001','11111','10001','10001','10001'],
              'B':['11110','10001','10001','11110','10001','10001','11110'],
              'C':['01111','10000','10000','10000','10000','10000','01111']}
    images={}
    for c,rows in patterns.items():
        im=Image.new('1',(16,16));d=ImageDraw.Draw(im)
        for y,row in enumerate(rows):
            for x,v in enumerate(row):
                if v=='1':d.rectangle((3+x*2,1+y*2,4+x*2,2+y*2),fill=1)
        images[c]=im
    for c in '가각갈곽이출 ':
        im=Image.new('1',(16,16));d=ImageDraw.Draw(im)
        if c=='가':d.line([(2,3),(7,3),(7,12)],fill=1);d.line([(11,1),(11,14)],fill=1);d.line([(11,7),(14,7)],fill=1)
        elif c in '각갈':
            d.line([(2,2),(7,2),(7,7)],fill=1);d.line([(11,1),(11,8)],fill=1);d.line([(11,4),(14,4)],fill=1)
            if c=='각':d.line([(3,10),(12,10),(12,14)],fill=1)
            else:d.line([(3,10),(12,10),(12,12),(3,12),(3,14),(12,14)],fill=1)
        elif c=='곽':
            d.line([(2,1),(7,1),(7,5)],fill=1);d.line([(1,7),(8,7)],fill=1);d.line([(5,5),(5,7)],fill=1)
            d.line([(11,1),(11,9)],fill=1);d.line([(11,5),(14,5)],fill=1);d.line([(3,11),(12,11),(12,14)],fill=1)
        elif c=='이':d.ellipse((2,3,8,11),outline=1);d.line([(12,1),(12,14)],fill=1)
        elif c=='출':
            d.line([(7,0),(7,1)],fill=1);d.line([(4,3),(11,3)],fill=1);d.line([(7,4),(3,6)],fill=1);d.line([(8,4),(12,6)],fill=1)
            d.line([(2,7),(13,7)],fill=1);d.line([(7,7),(7,9)],fill=1)
            d.line([(3,10),(12,10),(12,12),(3,12),(3,14),(12,14)],fill=1)
        images[c]=im
    chars='ABC가각갈곽이출 '
    glyphs={c:{'pixels':[''.join('#' if images[c].getpixel((x,y)) else '.' for x in range(16)) for y in range(16)]} for c in chars}
    save(folder/'glyphs.json',{'format':'bitmap-v1','glyphs':glyphs})
    b=brief('bitmap',chars);b['acceptance']['critical_pairs']=['가각','각갈','갈곽'];save(folder/'design-brief.json',b)
    atlas=Image.new('L',(64,48))
    for i,c in enumerate(chars):atlas.paste(images[c].convert('L'),((i%4)*16,(i//4)*16))
    atlas.save(folder/'reference.png');atlas.resize((512,384),Image.Resampling.NEAREST).save(ROOT/'assets/pixel16-reference-preview.png')
    folder=ROOT/'examples/vector';folder.mkdir(exist_ok=True)
    glyphs={
      'A':{'svg_path':'M 140 860 L 410 100 L 590 100 L 860 860 L 685 860 L 625 660 L 370 660 L 310 860 Z M 420 510 L 575 510 L 500 270 Z'},
      'B':{'svg_path':'M 200 100 L 530 100 C 850 100 900 440 700 495 C 930 570 850 860 530 860 L 200 860 Z M 375 270 L 375 420 L 515 420 C 665 420 665 270 515 270 Z M 375 575 L 375 690 L 530 690 C 680 690 680 575 530 575 Z'},
      'C':{'svg_path':'M 800 175 L 720 335 C 420 115 170 530 455 690 C 540 740 650 715 735 655 L 815 795 C 360 1070 0 570 280 220 C 425 35 645 60 800 175 Z'}}
    save(folder/'glyphs.json',{'format':'vector-v1','glyphs':glyphs});save(folder/'design-brief.json',brief('vector','ABC'))
    # Generate a reference directly from source path geometry, not an unrelated installed font.
    from make_font_with_ai.engine import make_font
    from make_font_with_ai.raster import Renderer
    import io
    f,_=make_font(brief('vector','ABC'),{'format':'vector-v1','glyphs':glyphs});buf=io.BytesIO();f.save(buf)
    renderer=Renderer(buf.getvalue(),brief('vector','ABC'));im=Image.new('L',(600,200))
    for i,c in enumerate('ABC'):im.paste(Image.fromarray(renderer.glyph(c,200)[0]),(i*200,0))
    im.save(folder/'reference.png');im.save(ROOT/'assets/vector-reference-preview.png')
    print('EXAMPLES_CREATED',len(chars),'pixel glyphs, 3 vector glyphs; briefs need explicit confirmation; no font binary saved.')
if __name__=='__main__':main()
