"""Reusable georeferenced map overlays and a self-contained English gallery."""
import base64
import html
import io
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageChops

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def rings_of(geometry):
    if 'rings' in geometry:return geometry['rings']
    if geometry['type']=='Polygon':return geometry['coordinates']
    if geometry['type']=='MultiPolygon':return [r for polygon in geometry['coordinates'] for r in polygon]
    raise ValueError('Only polygon map overlays are supported.')

def draw_map(base_file,extent,parcel,output,layers=None,soil_file=None,opacity=.5):
    if not 0<=opacity<=1:raise ValueError('Opacity must be between zero and one.')
    if extent.get('spatialReference',{}).get('wkid',4326)!=4326:
        raise ValueError('Map overlays require a WGS84 extent and WGS84 polygon inputs.')
    xmin,ymin,xmax,ymax=[extent[k] for k in ('xmin','ymin','xmax','ymax')]
    if not(xmax>xmin and ymax>ymin):raise ValueError('Invalid map extent.')
    with Image.open(base_file) as image:base=image.convert('RGBA')
    width,height=base.size
    xy=lambda p:((p[0]-xmin)/(xmax-xmin)*width,(ymax-p[1])/(ymax-ymin)*height)
    if soil_file:
        with Image.open(soil_file) as image:soil=image.convert('RGBA')
        if soil.size!=base.size:raise ValueError('Soil export dimensions must match the base image; confirm equal extents too.')
        alpha=soil.getchannel('A').point(lambda a:round(a*opacity));soil.putalpha(alpha)
        base=Image.alpha_composite(base,soil)
    for layer in layers or []:
        color=layer.get('color',[50,145,200,110])
        for feature in layer['features']:
            mask=Image.new('1',base.size)
            for ring in rings_of(feature.get('geometry',feature)):
                part=Image.new('1',base.size);ImageDraw.Draw(part).polygon([xy(p) for p in ring],fill=1)
                mask=ImageChops.logical_xor(mask,part)
            overlay=Image.new('RGBA',base.size,tuple(color))
            overlay.putalpha(mask.convert('L').point(lambda a:round(a*color[3]/255)))
            base=Image.alpha_composite(base,overlay)
    draw=ImageDraw.Draw(base)
    for ring in rings_of(parcel):
        points=[xy(p) for p in ring]
        draw.line(points,fill='white',width=6)
        draw.line(points,fill='#ff3f38',width=3)
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    base.convert('RGB').save(output)
    return str(Path(output).resolve())

def gallery(cards,output,title):
    body=[]
    for card in cards:
        path=Path(card['file'])
        with Image.open(path) as image:
            buffer=io.BytesIO();image.save(buffer,format='PNG')
        data=base64.b64encode(buffer.getvalue()).decode()
        body.append('<section><h2>'+html.escape(card['title'])+'</h2><img src="data:image/png;base64,'+data+'" alt="'+html.escape(card['title'],quote=True)+'"><p>'+html.escape(card.get('note',''))+'</p></section>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>body{font:16px/1.5 system-ui;background:#f1f4f6;color:#203347;margin:0}main{max-width:1100px;margin:auto;padding:24px}section{background:white;border-radius:12px;padding:20px;margin:24px 0}img{width:100%;height:auto}p{max-width:950px}</style><main><h1>'+html.escape(title)+'</h1>'+''.join(body)+'</main></html>'
    Path(output).write_text(page,encoding='utf-8')
    return str(Path(output).resolve())
