"""Append-only review requests; provider inputs are unverified data."""
import datetime as dt
import re
import uuid
import library


def folder(case_id,revision_id):
    if not isinstance(revision_id,str) or not re.fullmatch('[a-f0-9]{32}',revision_id):
        raise ValueError('Identificador de revisión inválido')
    return library.case_path(case_id)/'revisiones'/revision_id


def submit(case_id,claim_id,links='',context=''):
    if not isinstance(links,str) or not isinstance(context,str) or len(links)>100000 or len(context)>100000:
        raise ValueError('Enlaces y texto: máximo 100.000 caracteres por campo')
    case_folder=library.case_path(case_id)
    rows=library.read(case_folder/'claims.json',[])
    selected=[c for c in rows if c['id']==claim_id]
    if len(selected)!=1:raise ValueError('Afirmación inexistente en este expediente')
    ident=uuid.uuid4().hex;target=folder(case_id,ident);target.mkdir(parents=True)
    request={'id':ident,'case_id':case_id,'claim_id':claim_id,'claim':selected[0]['claim'],
             'submitted_at':dt.datetime.now(dt.timezone.utc).isoformat(),
             'supplied_links_unverified':links,'supplied_context_unverified':context}
    library.save(target/'request.json',request)
    library.save(target/'previous_claim.json',selected[0])
    for name in ('resultados.md','fuentes.md','auditoria.md'):
        path=case_folder/name
        if path.exists():library.write(target/('previous_'+name),path.read_text(encoding='utf-8'))
    update(case_id,ident,'queued')
    return request


def update(case_id,ident,status,**fields):
    target=folder(case_id,ident)/'status.json'
    current=library.read(target,{})
    library.save(target,{**current,**fields,'status':status,'updated_at':dt.datetime.now(dt.timezone.utc).isoformat()})


def load(case_id,ident,claim_id):
    request=library.read(folder(case_id,ident)/'request.json')
    if not request or request['case_id']!=case_id or request['claim_id']!=claim_id:
        raise ValueError('La revisión no corresponde a la afirmación y expediente')
    return request


def history(case_id):
    result=[]
    for path in (library.case_path(case_id)/'revisiones').glob('*/request.json'):
        request=library.read(path)
        if request:result.append({'id':request['id'],'claim_id':request['claim_id'],
                                 'submitted_at':request['submitted_at'],
                                 **library.read(path.parent/'status.json',{})})
    return sorted(result,key=lambda r:r['submitted_at'],reverse=True)
