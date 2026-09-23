"""Optional human observations, separate from automatic verdicts."""
import datetime as dt
import hashlib
import json
import uuid
import library

DECISIONS={'supports':'Considero que respalda la afirmación','insufficient':'Considero que el respaldo es insuficiente',
           'contradicts':'Encontré una contradicción','uncertain':'No puedo decidir con este material'}

def fingerprint(claim):
    payload={'id':claim['id'],'claim':claim['claim'],'status':claim['status'],'evidence':claim.get('evidence',[])}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()

def history(case_id):
    folder=library.case_path(case_id)/'revisiones-humanas'
    return sorted([library.read(p) for p in folder.glob('*.json')],key=lambda r:r['reviewed_at'],reverse=True)

def record(case_id,claim_id,actor,decision,indices,notes,limits,expected_fingerprint):
    folder=library.case_path(case_id)
    claim=next((c for c in library.read(folder/'claims.json',[]) if c['id']==claim_id),None)
    if not claim:raise ValueError('Afirmación inexistente en este expediente')
    if fingerprint(claim)!=expected_fingerprint:raise ValueError('La afirmación o su evidencia cambió; vuelve a abrir la ficha antes de guardar')
    if decision not in DECISIONS:raise ValueError('Selecciona una observación válida')
    if not isinstance(actor,str) or not actor.strip() or len(actor)>120:raise ValueError('Indica quién revisó (máximo 120 caracteres)')
    if not isinstance(notes,str) or not notes.strip() or len(notes)>4000:raise ValueError('Describe qué comprobaste (máximo 4000 caracteres)')
    if not isinstance(limits,str) or not limits.strip() or len(limits)>4000:raise ValueError('Indica los límites o dudas que quedan (máximo 4000 caracteres)')
    evidence=claim.get('evidence',[])
    if not isinstance(indices,list) or not indices or any(type(i)!=int or not 0<=i<len(evidence) for i in indices) or len(indices)!=len(set(indices)):
        raise ValueError('Selecciona al menos una fuente que realmente examinaste')
    receipt={'id':uuid.uuid4().hex,'case_id':case_id,'claim_id':claim_id,'claim':claim['claim'],
             'automatic_status_at_review':claim['status'],'claim_fingerprint':expected_fingerprint,
             'reviewed_at':dt.datetime.now(dt.timezone.utc).isoformat(),'actor':actor.strip(),
             'decision':decision,'notes':notes.strip(),'limits':limits.strip(),
             'examined_evidence':[{'index':i,'evidence':evidence[i]} for i in indices],
             'automatic_verdict_changed':False}
    target=folder/'revisiones-humanas';target.mkdir(exist_ok=True)
    with (target/(receipt['id']+'.json')).open('x',encoding='utf-8') as stream:
        json.dump(receipt,stream,ensure_ascii=False,indent=2)
    rows=history(case_id)
    text='# Revisiones humanas\n\nObservaciones opcionales. No modifican veredictos automáticos ni resuelven el cierre científico por sí solas.\n\n'
    for r in rows:
        text+=f'## {r["claim"]}\n\n{r["reviewed_at"]} · {r["actor"]}\n\nObservación: {DECISIONS[r["decision"]]}\n\nFuentes examinadas: '+', '.join(str(e['index']+1) for e in r['examined_evidence'])+f'\n\nQué comprobó: {r["notes"]}\n\nLímites: {r["limits"]}\n\nVeredicto automático conservado: {r["automatic_status_at_review"]}.\n\n'
    library.write(folder/'revisiones-humanas.md',text)
    return receipt
