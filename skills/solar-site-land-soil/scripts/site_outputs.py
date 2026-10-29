"""Generate consistent English reports, validate metrics and export three PDFs."""
import html
import json
import re
import textwrap
from pathlib import Path
import assess

LABELS={'arn':'ARN','pin':'PIN','soil':'Agricultural soil capability','slope_full_area':'Full-parcel slope','solar_permitted_use':'Ground-mounted solar permitted use'}

def label(key):return LABELS.get(key,key.replace('_',' ').title())

def overview(value,limit=600):
    if value is None:return 'Unknown'
    if isinstance(value,dict):
        value={k:v for k,v in value.items() if k not in ('geometry','coordinates','rings','tests','query_provenance')}
    result=json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else str(value)
    return result if len(result)<=limit else result[:limit]+' ... [see structured evidence]'

def readable(value,depth=0):
    """Format structured observations without inventing an interpretation."""
    if value is None:return ['Unknown']
    if isinstance(value,bool):return ['Yes' if value else 'No']
    if isinstance(value,dict):
        lines=[]
        for key,item in value.items():
            if key in ('geometry','coordinates','rings','tests','query_provenance'):continue
            if isinstance(item,(dict,list)):
                lines.extend(['**'+label(key)+'**',''])
                lines.extend(readable(item,depth+1) if depth<2 else [overview(item,1000)])
            else:lines.append('**'+label(key)+':** '+readable(item,depth+1)[0])
            lines.append('')
        return lines or ['See structured geometry in assessment.json.']
    if isinstance(value,list):
        if all(not isinstance(v,(dict,list)) for v in value):return [', '.join(readable(v)[0] for v in value) or 'No entries recorded.']
        lines=[]
        for index,item in enumerate(value[:8]):
            lines.extend(['**Entry '+str(index+1)+'**','',*readable(item,depth+1),''])
        if len(value)>8:lines.append('Additional entries retained in assessment.json.')
        return lines
    return [str(value)]

def display_value(key,value):
    """Select report detail; complete source attributes stay in assessment.json."""
    if key=='address_candidates' and isinstance(value,list):
        return {'candidate_count':len(value),'scope':'Unselected geocoder candidates; use the separately confirmed parcel location. Complete candidates are retained in assessment.json.'}
    if key=='soil' and isinstance(value,dict):
        value=dict(value)
        if isinstance(value.get('mapping_units'),list):
            value['mapping_units']=[{k:v for k,v in unit.items() if k=='OBJECTID' or k.startswith(('CLI','PERCENT','SOIL_NAME')) or k in ('components','objectid')} for unit in value['mapping_units']]
        return value
    if key=='wetlands' and isinstance(value,dict):
        value=dict(value)
        if isinstance(value.get('intersecting_polygons'),list):
            value['intersecting_polygons']=[{k:v for k,v in unit.items() if any(word in k.upper() for word in ('OBJECTID','NAME','STATUS','SIGNIF','ACCURACY'))} for unit in value['intersecting_polygons']]
        return value
    return value

def validate_report(report,root=None):
    errors=[];warnings=[]
    statuses={'verified','provided','estimated','needs_review','skipped'}
    for key,item in report.get('metrics',{}).items():
        if item.get('status') not in statuses:errors.append(key+': invalid status')
        if item.get('status')=='skipped':
            if item.get('value') is not None or not item.get('reason'):errors.append(key+': invalid skipped metric')
        elif item.get('value') is None:errors.append(key+': missing value')
        elif not item.get('source'):warnings.append(key+': source missing')
        if item.get('status')!='skipped' and not item.get('retrieved_at'):warnings.append(key+': retrieval timestamp missing')
    if not report.get('metrics'):errors.append('No assessment metrics supplied.')
    if report.get('overall_project_decision') is not None:errors.append('Overall decision must remain unresolved in public screening.')
    if report.get('capacity_reserved') is True:errors.append('Public screening does not reserve capacity.')
    return {'valid':not errors,'errors':errors,'warnings':warnings}

def render(report):
    address=report.get('input',{}).get('normalized_address') or report.get('input',{}).get('address') or 'Site not specified'
    lines=['# Ontario Solar Site Evaluation','',address,'','Generated: '+report.get('generated_at','Unknown'),'',
        'Public-source screening. Missing indicators are unknown, not a failure or zero. No development approval or overall project Pass/Fail is assigned.','',
        '| Indicator | Status | Result or reason |','|---|---|---|']
    for key,item in report.get('metrics',{}).items():
        value=item.get('reason') if item['status']=='skipped' else overview(display_value(key,item.get('value')),220)
        lines.append('| '+label(key)+' | '+item['status']+' | '+str(value).replace('|','\\|').replace('\n',' ')+' |')
    for key,item in report.get('metrics',{}).items():
        lines.extend(['','## '+label(key),''])
        lines.extend([item.get('reason','Not collected')] if item['status']=='skipped' else readable(display_value(key,item.get('value'))))
        for field in ('source','retrieved_at','data_date','evidence_locator','scope'):
            if item.get(field):lines.extend(['',label(field)+': '+str(item[field])])
    if report.get('findings'):lines.extend(['','## Findings','',*readable(report['findings'])])
    lines.extend(['','## Evidence and limits','','GeoWarehouse is excluded. Capacity-map observations and calculator trials do not reserve capacity. Planning interpretations require operative provisions and amendments. Exact values and retained uncertainty are in assessment.json.',''])
    return '\n'.join(lines)

def write_report(report,out):
    validation=validate_report(report)
    if not validation['valid']:raise ValueError('; '.join(validation['errors']))
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    assess.save_json(out/'assessment.json',report)
    (out/'report.md').write_text(render(report),encoding='utf-8')
    assess.save_json(out/'validation.json',validation)
    return {'assessment':str((out/'assessment.json').resolve()),'report':str((out/'report.md').resolve()),'validation':validation}

def export_pdfs(report_file,assessment_file,cards,out):
    """ReportLab/Pillow/pypdf are optional; no browser or fixed runtime paths."""
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,Preformatted
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from pypdf import PdfReader
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    report=json.loads(Path(assessment_file).read_text(encoding='utf-8-sig'))
    address=report.get('input',{}).get('address') or 'Solar Site Evaluation'
    styles=getSampleStyleSheet()
    styles['Heading2'].keepWithNext=True
    styles.add(ParagraphStyle(name='SolarBody',fontName='Helvetica',fontSize=9,leading=12,spaceAfter=6))
    styles.add(ParagraphStyle(name='SolarCell',parent=styles['SolarBody'],fontSize=7.5,leading=10,spaceAfter=0))
    styles.add(ParagraphStyle(name='SolarCode',fontName='Courier',fontSize=7,leading=9))
    def inline(text):
        text=html.escape(text.replace('\u2013','-').replace('\u2014','-').replace('\u2011','-').replace('\u00d7',' x '))
        text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\1',text)
        text=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',text)
        return re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',text)
    def para(text,style='SolarBody'):return Paragraph(inline(text),styles[style])
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#647586'))
        canvas.drawString(42,23,'Solar Site Evaluation | '+report.get('generated_at','Unknown')[:10])
        canvas.drawRightString(A4[0]-42,23,str(doc.page))
    def build(name,story,title):
        path=out/name
        SimpleDocTemplate(str(path),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=48,title=title).build(story,onFirstPage=footer,onLaterPages=footer)
        reader=PdfReader(path)
        if not reader.pages or any(not p.extract_text().strip() for p in reader.pages):raise ValueError('Empty PDF page produced.')
        return {'file':str(path.resolve()),'pages':len(reader.pages)}
    story=[];lines=Path(report_file).read_text(encoding='utf-8').splitlines();i=0;code=False
    while i<len(lines):
        line=lines[i].strip();i+=1
        if not line:continue
        if line.startswith('```'):code=not code;continue
        if code:
            for part in textwrap.wrap(line,110,replace_whitespace=False,drop_whitespace=False):story.append(Preformatted(part,styles['SolarCode']))
        elif line.startswith('|'):
            tablelines=[line]
            while i<len(lines) and lines[i].strip().startswith('|'):tablelines.append(lines[i].strip());i+=1
            rows=[]
            for row in tablelines:
                cells=re.split(r'(?<!\\)\|',row.strip('|'))
                if all(re.fullmatch(r'\s*[-:]+\s*',c) for c in cells):continue
                rows.append([para(c.strip().replace('\\|','|'),'SolarCell') for c in cells])
            n=len(rows[0]);width=A4[0]-84
            widths=[width*.27,width*.18,width*.55] if n==3 else [width/n]*n
            table=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5eef4')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f7f9fb')]),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([table,Spacer(1,10)])
        elif line.startswith('# '):story.append(para(line[2:],'Title'))
        elif line.startswith('## '):story.append(para(line[3:],'Heading2'))
        elif not line.startswith('!['):story.append(para(line))
    results={'report':build('assessment-report.pdf',story,'Solar Site Evaluation')}
    story=[]
    from PIL import Image as PILImage
    for card in cards:
        if story:story.append(PageBreak())
        story.extend([para(card['title'],'Title'),para(address)])
        with PILImage.open(card['file']) as image:w,h=image.size
        scale=min((A4[0]-84)/w,520/h)
        story.extend([Image(card['file'],width=w*scale,height=h*scale),Spacer(1,12),para(card.get('note',''))])
    if not story:story=[para('Site Maps','Title'),para('No map inputs supplied. Map generation remains uncollected.')]
    results['maps']=build('site-maps.pdf',story,'Solar Site Maps')
    story=[para('Structured Assessment Data','Title'),para(address),para('Complete assessment.json, wrapped for printing. Retain the original JSON for machine use.')]
    raw=Path(assessment_file).read_text(encoding='utf-8-sig')
    for line in raw.splitlines():
        for part in textwrap.wrap(line,110,replace_whitespace=False,drop_whitespace=False,break_on_hyphens=False) or ['']:
            story.append(Preformatted(part,styles['SolarCode']))
    results['data']=build('assessment-data.pdf',story,'Structured Assessment Data')
    return results
