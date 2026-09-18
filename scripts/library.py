"""Persistent case catalogue and generated navigation for the research vault."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import unicodedata
import uuid
from urllib.parse import quote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / '.project-intelligence/library'


def read(path, fallback=None):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError): return fallback


def save(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(text, encoding='utf-8')
    os.replace(temp, path)


def case_path(case_id):
    if not re.fullmatch(r'[a-z0-9-]{1,100}', case_id): raise ValueError('Expediente inválido')
    path = (BASE / case_id).resolve()
    if BASE.resolve() not in path.parents: raise ValueError('Expediente fuera de biblioteca')
    return path


def tags(value):
    values = value.split(',') if isinstance(value, str) else value
    result = []
    for item in values[:20]:
        tag = unicodedata.normalize('NFKD', str(item).strip().lstrip('#')).encode('ascii','ignore').decode().lower()
        tag = re.sub(r'[^a-z0-9/_-]+','-',tag).strip('-/')[:60]
        if tag and any(c.isalpha() for c in tag) and tag not in result: result.append(tag)
    return result


def create(title, question, links, labels, brief, materials):
    title = re.sub(r'[\[\]|\r\n]', ' ', title).strip()[:160] or question.splitlines()[0][:120]
    slug = re.sub('[^a-z0-9]+','-', unicodedata.normalize('NFKD',title).encode('ascii','ignore').decode().lower()).strip('-')[:45] or 'investigacion'
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    case_id = stamp[:10]+'-'+slug+'-'+uuid.uuid4().hex[:8]
    folder = case_path(case_id);folder.mkdir(parents=True)
    meta = {'id':case_id,'title':title,'question':question,'links':links,'tags':tags(labels),
            'created_at':stamp,'updated_at':stamp,'status':'queued','brief':str(brief),
            'materials':materials,'claim_ids':[],'error':''}
    save(folder/'case.json',meta)
    for material in materials:
        source=(ROOT/material['path']).resolve()
        if ROOT not in source.parents: raise ValueError('Adjunto fuera del proyecto')
        target=folder/'adjuntos'/source.name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(source.read_bytes())
        material['case_path']='adjuntos/'+source.name
    save(folder/'case.json',meta)
    write(folder/'pregunta.md','# Pregunta\n\n'+question+'\n\n## Materiales aportados (no verificados)\n\n'+links+'\n')
    write(folder/'notas.md','# Mis notas\n\nEspacio personal. No se regenera con las pasadas de IA.\n')
    write(folder/'resultados.md','# Resultados\n\nPendientes de investigación y revisión.\n')
    write(folder/'fuentes.md','# Fuentes\n\nTodavía no hay fuentes verificadas registradas.\n')
    write(folder/'auditoria.md','# Auditoría\n\nPendiente de revisión crítica.\n')
    refresh()
    return case_id


def all_cases():
    return [m for p in BASE.glob('*/case.json') if (m:=read(p))]


def get_rows(meta, rows):
    return [c for c in rows if c.get('investigation_id')==meta['id'] or c['id'] in meta.get('claim_ids',[])]


def set_status(case_id, status, error=''):
    path=case_path(case_id)/'case.json';meta=read(path)
    if meta is None: raise ValueError('No existe el expediente')
    meta.update(status=status,error=error,updated_at=dt.datetime.now(dt.timezone.utc).isoformat())
    save(path,meta);refresh()


def canonical_url(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path,p.query,''))


def refresh(rows=None):
    if rows is None:
        rows=[]
        for group in ('architecture','dependencies','changes'):
            rows.extend(read(ROOT/'.project-intelligence/claims'/f'{group}.json',[]))
    cases=all_cases();catalogue={}
    for meta in cases:
        folder=case_path(meta['id']);selected=get_rows(meta,rows)
        meta['claim_ids']=[c['id'] for c in selected]
        meta['counts']={s:sum(c['status']==s for c in selected) for s in ('UNVERIFIED','VERIFIED','PARTIAL','UNSUPPORTED','CONTRADICTED')}
        meta['summary']=f"{len(selected)} afirmaciones; {meta['counts']['VERIFIED']} verificadas; {sum(c.get('sensible') is True or c.get('favorable') is True for c in selected)} con banderas de auditoría."
        meta['search_text']=' '.join([meta['title'],meta.get('question',''),meta.get('links',''),*meta.get('tags',[]),*[c['claim'] for c in selected]]).casefold()
        save(folder/'claims.json',selected)
        sources=[]
        for c in selected:
            for e in c.get('evidence',[]):
                if e.get('type')!='external':continue
                url=canonical_url(e['url']);source=catalogue.setdefault(url,{'url':url,'title':e.get('title',url),'cases':[],'claims':[]})
                if meta['id'] not in source['cases']:source['cases'].append(meta['id'])
                if c['id'] not in source['claims']:source['claims'].append(c['id'])
                if url not in sources:sources.append(url)
        meta['source_urls']=sources
        save(folder/'case.json',meta)
    for meta in cases:
        folder=case_path(meta['id']);related=[c for c in cases if c['id']!=meta['id'] and (set(c.get('tags',[])) & set(meta.get('tags',[])) or set(c.get('source_urls',[])) & set(meta.get('source_urls',[])))]
        metadata='---\ntitle: '+json.dumps(meta['title'],ensure_ascii=False)+'\ntags:\n'+''.join('  - '+t+'\n' for t in ['tipo/investigacion','estado/'+meta['status'],*meta.get('tags',[])])+'case_id: '+meta['id']+'\n---\n'
        text=metadata+'# '+meta['title']+'\n\n'+meta['summary']+'\n\nEstado de ejecución: '+meta['status']+' (distinto del veredicto de las afirmaciones).\n\n'
        for name,label in [('pregunta','Pregunta y contexto'),('resultados','Resultados'),('fuentes','Fuentes y procedencia'),('auditoria','Auditoría'),('notas','Mis notas')]:
            text+='- [[Investigaciones/'+meta['id']+'/'+name+'|'+label+']]\n'
        if meta.get('materials'):
            text+='\n## Adjuntos\n\n'+''.join('- [['+'Investigaciones/'+meta['id']+'/'+m['case_path']+'|'+m['name']+']] — '+m['analysis']+'\n' for m in meta['materials'])
        text+='\n## Investigaciones relacionadas\n\nRelación por etiquetas o fuentes compartidas; no implica corroboración independiente.\n\n'
        text+=''.join('- [[Investigaciones/'+c['id']+'/resumen|'+c['title']+']]\n' for c in related) or 'Todavía no hay relaciones registradas.\n'
        if meta.get('error'):text+='\n## Último error\n\n'+meta['error']+'\n'
        write(folder/'resumen.md',text)
    save(BASE/'sources.json',list(catalogue.values()))
    write(BASE/'Biblioteca.md','# Biblioteca de investigaciones\n\n[[Temas|Explorar por temas]] · [[Fuentes|Catálogo de fuentes]] · [[Guia|Cómo usar el cerebro de investigación]]\n\n'+''.join('- [[Investigaciones/'+m['id']+'/resumen|'+m['title']+']] — '+m['status']+' — '+m['summary']+'\n' for m in sorted(cases,key=lambda c:c['created_at'],reverse=True)))
    text='# Temas\n\n'
    for tag in sorted({t for m in cases for t in m.get('tags',[])}):
        text+='## #'+tag+'\n\n'+''.join('- [[Investigaciones/'+m['id']+'/resumen|'+m['title']+']]\n' for m in cases if tag in m.get('tags',[]))+'\n'
    write(BASE/'Temas.md',text)
    text='# Fuentes\n\nFuentes registradas en evidencias, no enlaces aportados todavía sin revisar. Compartir una URL no constituye dos fuentes independientes.\n\n'
    for source in catalogue.values():
        text+='- ['+source['title'].replace('[','').replace(']','')+']('+source['url']+')\n'+''.join('  - [[Investigaciones/'+cid+'/resumen]]\n' for cid in source['cases'])
    write(BASE/'Fuentes.md',text)


def uri(case_id):
    config=read(ROOT/'.project-intelligence/obsidian.json',{})
    vault=Path(config.get('vault_path','')).name
    return 'obsidian://open?vault='+quote(vault,safe='')+'&file='+quote('Investigaciones/'+case_id+'/resumen',safe='')
