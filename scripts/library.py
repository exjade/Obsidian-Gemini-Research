"""Persistent case catalogue and generated navigation for the research vault."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import unicodedata
import uuid
import source_check
import source_identity
import source_metadata
import source_resolver
from urllib.parse import quote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / '.project-intelligence/library'


def needs_review(claim):
    if claim.get('status') != 'VERIFIED':
        return True
    external = [e for e in claim.get('evidence', []) if e.get('type') == 'external']
    return any(not (source_check.latest(e, ROOT / '.project-intelligence/source-checks') or {}).get('eligible') for e in external)


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


def related_cases(cases, meta):
    """Relate by shared topic tags or canonical source IDs, never raw legacy URLs."""
    return [case for case in cases if case['id']!=meta['id'] and
            (set(case.get('tags',[])) & set(meta.get('tags',[])) or
             set(case.get('source_ids',[])) & set(meta.get('source_ids',[])))]


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
        source_ids=[]
        for c in selected:
            for index,e in enumerate(c.get('evidence',[])):
                sid=e.get('source_id');eid=e.get('evidence_id')
                # Legacy records without persisted policy IDs remain outside the catalogue.
                if not source_identity.has_catalog_identity(e):continue
                source=catalogue.setdefault(sid,{'source_id':sid,'identity_policy':e['source_identity_policy'],
                    'title':e.get('title',''),'url':e.get('url',''),'type':e.get('type','unknown'),
                    'references':[],'case_ids':[],'claim_ids':[],'passages':{},'metadata_assertions':[],
                    'metadata_resolutions':[]})
                reference={k:e[k] for k in ('type','url','title','doi','pmid','pmcid','document_sha256') if e.get(k) not in (None,'')}
                if reference and reference not in source['references']:source['references'].append(reference)
                for field,value in (('title',e.get('title')),('url',e.get('url')),('doi',e.get('doi')),
                                    ('pmid',e.get('pmid')),('pmcid',e.get('pmcid')),
                                    ('document_sha256',e.get('document_sha256')),('source_type',e.get('type'))):
                    assertion=source_metadata.assertion(field,value,'evidence.declared.'+field,'declared',reference=eid)
                    if assertion and assertion not in source['metadata_assertions']:
                        source['metadata_assertions'].append(assertion)
                if e.get('type')=='external' and e.get('source_check_id'):
                    for assertion in source_check.trusted_metadata(e,ROOT/'.project-intelligence/source-checks'):
                        if assertion not in source['metadata_assertions']:
                            source['metadata_assertions'].append(assertion)
                # Reuse only integrity-checked, already-persisted lookups bound to
                # this source and a metadata identifier already present locally.
                known_lookup_values={
                    (item['field'], source_metadata.normalize_identifier(item['field'], item['value']))
                    for item in source['metadata_assertions']
                    if item.get('field') in ('doi','pmid','pmcid')
                }
                for receipt in source_resolver.trusted_receipts_for_source(ROOT,sid):
                    lookup=(receipt.get('lookup_field'),receipt.get('lookup_value'))
                    if lookup not in known_lookup_values:
                        continue
                    summary={key:receipt.get(key) for key in
                             ('id','provider','lookup_field','lookup_value','retrieved_at','outcome')}
                    if receipt.get('error'):
                        summary['error']=receipt['error'][:300]
                    if summary not in source['metadata_resolutions']:
                        source['metadata_resolutions'].append(summary)
                    for assertion in source_metadata.resolution_assertions(receipt):
                        if assertion not in source['metadata_assertions']:
                            source['metadata_assertions'].append(assertion)
                if meta['id'] not in source['case_ids']:source['case_ids'].append(meta['id'])
                if c['id'] not in source['claim_ids']:source['claim_ids'].append(c['id'])
                passage=source['passages'].setdefault(eid,{'evidence_id':eid,'excerpt':e.get('excerpt',''),
                    'physical_page':e.get('physical_page'),'chunk_id':e.get('chunk_id'),'lines':e.get('lines'),
                    'extraction_id':e.get('extraction_id'),'relationships':[]})
                rel={'case_id':meta['id'],'claim_id':c['id'],'evidence_id':eid,
                     'role':source_identity.normalize_relation(e.get('relation')),
                     'relation_type':'claim_passage','location':{k:e.get(k) for k in ('physical_page','chunk_id','lines','extraction_id') if e.get(k) is not None}}
                if rel not in passage['relationships']:passage['relationships'].append(rel)
                if sid not in source_ids:source_ids.append(sid)
        meta['source_ids']=sorted(source_ids)
        save(folder/'case.json',meta)
    for meta in cases:
        folder=case_path(meta['id']);related=related_cases(cases,meta)
        metadata='---\ntitle: '+json.dumps(meta['title'],ensure_ascii=False)+'\ntags:\n'+''.join('  - '+t+'\n' for t in ['tipo/investigacion','estado/'+meta['status'],*meta.get('tags',[])])+'case_id: '+meta['id']+'\n---\n'
        text=metadata+'# '+meta['title']+'\n\n'+meta['summary']+'\n\nEstado de ejecución: '+meta['status']+' (distinto del veredicto de las afirmaciones).\n\n'
        selected=read(folder/'claims.json',[])
        tone={'running':'info','queued':'info','error':'failure','interrupted':'warning'}.get(meta['status'],'success')
        label={'running':'En curso — espera a que termine','queued':'En espera','error':'Error — requiere atención','interrupted':'Interrumpida — puedes reintentar','completed':'Ejecución finalizada','historical':'Expediente histórico'}.get(meta['status'],meta['status'])
        text+='> [!'+tone+'] '+label+'\n> Finalizar una ejecución no verifica todas las afirmaciones.\n\n'
        pending=[c for c in selected if needs_review(c)]
        if pending:
            text+='> [!warning] '+str(len(pending))+' afirmaciones necesitan revisión\n> Consulta Fuentes y Auditoría; aporta respaldo en la ficha del frontend para reevaluar.\n\n'
        closure=meta.get('closure')
        if closure:
            text+='> [!'+('success' if meta.get('publication',{}).get('consolidated') else 'warning')+'] '+('Resultados consolidados en la última ejecución' if meta.get('publication',{}).get('consolidated') else 'Informe provisional — investigación inconclusa')+'\n> Hipótesis resueltas: '+str(closure['resolved'])+'/'+str(closure['total'])+'. Estado de la última ejecución; consulta el frontend para comprobaciones actuales.\n\n'
            for item in closure.get('blockers',[]):
                text+='> [!warning] Falta resolver\n> '+item.get('claim','Alcance pendiente').replace('\n',' ')+'\n> '+item['reason'].replace('\n',' ')+'\n> Siguiente acción: '+item['action']+'\n\n'
        text+='## Estado de cada afirmación\n\n'
        for c in selected:
            verdict=c.get('status','UNVERIFIED');ctone={'VERIFIED':'success','CONTRADICTED':'failure','UNSUPPORTED':'warning','PARTIAL':'warning'}.get(verdict,'info')
            if verdict=='VERIFIED' and needs_review(c):
                ctone='warning';verdict+=' — fuentes pendientes de comprobación'
            text+='> [!'+ctone+'] '+verdict+'\n> '+c['claim'].replace('\n',' ')+'\n> Motivo registrado: '+str(c.get('skeptic_note','Pendiente')).replace('\n',' ')+'\n\n'
        for name,label in [('pregunta','Pregunta y contexto'),('resultados','Resultados'),('fuentes','Fuentes y procedencia'),('auditoria','Auditoría'),('notas','Mis notas')]:
            text+='- [[Investigaciones/'+meta['id']+'/'+name+'|'+label+']]\n'
        if meta.get('materials'):
            text+='\n## Adjuntos\n\n'+''.join('- [['+'Investigaciones/'+meta['id']+'/'+m['case_path']+'|'+m['name']+']] — '+m['analysis']+'\n' for m in meta['materials'])
        text+='\n## Investigaciones relacionadas\n\nRelación por etiquetas o fuentes compartidas; no implica corroboración independiente.\n\n'
        text+=''.join('- [[Investigaciones/'+c['id']+'/resumen|'+c['title']+']]\n' for c in related) or 'Todavía no hay relaciones registradas.\n'
        if meta.get('error'):text+='\n## Último error\n\n'+meta['error']+'\n'
        write(folder/'resumen.md',text)
    catalogue_rows=[]
    for source in catalogue.values():
        source['case_ids']=sorted(source['case_ids']);source['claim_ids']=sorted(source['claim_ids'])
        source['metadata_resolutions']=sorted(source['metadata_resolutions'],
            key=lambda r:(r.get('lookup_field',''),r.get('lookup_value',''),r.get('provider',''),r.get('id','')))
        source['references']=sorted(source['references'],key=lambda ref:json.dumps(ref,sort_keys=True,ensure_ascii=False))
        source['metadata']=source_metadata.consolidate(source.pop('metadata_assertions',[]))
        # Preserve legacy top-level display fields as deterministic convenience values.
        if source['references']:
            preferred=source['references'][0]
            for key in ('title','url','type'):
                if preferred.get(key):source[key]=preferred[key]
        source['passages']=[dict(p,relationships=sorted(p['relationships'],key=lambda r:(r['case_id'],r['claim_id'],r['role'])))
                            for p in sorted(source['passages'].values(),key=lambda p:p['evidence_id'])]
        catalogue_rows.append(source)
    catalogue_rows.sort(key=lambda s:s['source_id'])
    save(BASE/'sources.json',{'policy':source_identity.CATALOG_POLICY,'sources':catalogue_rows,
        'legacy_uncatalogued_count':sum(1 for c in rows for e in c.get('evidence',[]) if not source_identity.has_catalog_identity(e))})
    write(BASE/'Biblioteca.md','# Biblioteca de investigaciones\n\n[[Temas|Explorar por temas]] · [[Fuentes|Catálogo de fuentes]] · [[Guia|Cómo usar el cerebro de investigación]]\n\n'+''.join('- [[Investigaciones/'+m['id']+'/resumen|'+m['title']+']] — '+m['status']+' — '+m['summary']+'\n' for m in sorted(cases,key=lambda c:c['created_at'],reverse=True)))
    text='# Temas\n\n'
    for tag in sorted({t for m in cases for t in m.get('tags',[])}):
        text+='## #'+tag+'\n\n'+''.join('- [[Investigaciones/'+m['id']+'/resumen|'+m['title']+']]\n' for m in cases if tag in m.get('tags',[]))+'\n'
    write(BASE/'Temas.md',text)
    text='# Fuentes\n\nFuentes registradas en evidencias, no enlaces aportados todavía sin revisar. Compartir una URL no constituye dos fuentes independientes.\n\n'
    text+='Los IDs agrupan según señales de identidad; no demuestran autenticidad, credibilidad, corroboración independiente ni verdad. Los roles pertenecen a la relación entre afirmación y pasaje.\n\n'
    text+='Los metadatos locales se complementan únicamente con recibos bibliográficos explícitos, íntegros y ligados a identificadores ya registrados. Actualizar esta vista no consulta la red. La resolución bibliográfica no confirma autenticidad, independencia científica, apoyo semántico ni verdad; los conflictos quedan visibles y no cambian la identidad de la fuente.\n\n'
    for source in catalogue_rows:
        title=(source['title'] or source.get('url') or source['source_id']).replace('[','').replace(']','')
        link='('+source['url']+')' if source.get('url') else ''
        text+='- '+title+' · fuente `'+source['source_id'][:12]+'`'+(' '+link if link else '')+'\n'
        metadata=source.get('metadata',{});identifiers=[]
        for field,label in (('doi','DOI'),('pmid','PMID'),('pmcid','PMCID')):
            item=metadata.get('fields',{}).get(field,{})
            if item.get('value'):identifiers.append(label+': '+item['value'])
        if identifiers:text+='  - Identificadores locales: '+', '.join(identifiers)+'\n'
        if metadata.get('conflicts'):
            names=', '.join(sorted({item['field'] for item in metadata['conflicts']}))
            text+='  - Conflictos de metadatos por resolver: '+names+'; no se eligió un valor canónico.\n'
        for resolution in source.get('metadata_resolutions',[]):
            text+='  - Resolución bibliográfica explícita: '+str(resolution.get('provider','proveedor'))+' · '+str(resolution.get('lookup_field','identificador')).upper()+' '+str(resolution.get('lookup_value',''))+' · '+str(resolution.get('outcome','estado desconocido'))+' ('+str(resolution.get('retrieved_at','fecha desconocida'))+'). No acredita autenticidad ni apoyo científico.\n'
        for ref in source['references']:
            if ref.get('url') and ref.get('url')!=source.get('url'):
                text+='  - Referencia: '+((ref.get('title')+' · ') if ref.get('title') else '')+ref['url']+' ('+str(ref.get('type','tipo no registrado'))+')\n'
        for passage in source['passages']:
            text+='  - Pasaje `'+passage['evidence_id'][:12]+'`\n'
            for rel in passage['relationships']:
                role={'support':'apoyo','contradiction':'contradicción','context':'contexto','unreviewed':'sin revisar'}[rel['role']]
                text+='    - [['+'Investigaciones/'+rel['case_id']+'/resumen|'+rel['case_id']+']] · afirmación `'+rel['claim_id']+'` · '+role+'\n'
    write(BASE/'Fuentes.md',text)


def uri(case_id):
    config=read(ROOT/'.project-intelligence/obsidian.json',{})
    vault=Path(config.get('vault_path','')).name
    return 'obsidian://open?vault='+quote(vault,safe='')+'&file='+quote('Investigaciones/'+case_id+'/resumen',safe='')
