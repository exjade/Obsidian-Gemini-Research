"""Compare recorded workflows, never invented quality or live provider runs."""
import argparse
import hashlib
import json
from pathlib import Path

def metrics(data):
    rows={c['id']:c for c in data['claims']}
    ids=data['approved_claim_ids']
    if len(set(ids))!=len(ids) or not ids or any(i not in rows for i in ids):
        raise ValueError('Alcance vacío, duplicado o incompleto en el registro.')
    selected=[rows[i] for i in ids]
    receipts=data.get('receipts')
    unique={(r['run_id'],r['stage']):r for r in receipts} if receipts is not None else None
    known=list(unique.values()) if unique is not None else []
    complete=unique is not None and bool(known) and all(isinstance(r.get('elapsed_seconds'),(float,int)) for r in known)
    judged=data.get('audited_claims')
    if judged is not None and (len({r['id'] for r in judged})!=len(judged) or any(r['id'] not in ids for r in judged)):
        raise ValueError('La revisión de calidad no corresponde al alcance.')
    if judged is not None and any(r.get('decision') not in ('correct','error','uncertain') for r in judged):
        raise ValueError('Revisión de calidad sin decisión válida: correct, error o uncertain.')
    signature={'question':data['question'],'claims':sorted(c['claim'] for c in selected)}
    return {'scope_sha256':hashlib.sha256(json.dumps(signature,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
            'scope_total':len(ids),'critical_reviews_recorded':sum(c.get('status') in ('VERIFIED','PARTIAL','UNSUPPORTED','CONTRADICTED') for c in selected),
            'claims_with_passages':sum(bool(c.get('evidence')) for c in selected),
            'verified_verdicts_recorded':sum(c.get('status')=='VERIFIED' for c in selected),
            'calls_recorded':len(known) if unique is not None else None,
            'failed_calls_recorded':sum(r.get('status')=='failed' for r in known) if unique is not None else None,
            'total_call_seconds_recorded':sum(r['elapsed_seconds'] for r in known) if complete else None,
            'quality_reviewed_claims':len(judged) if judged is not None else None,
            'quality_uncertain_claims':sum(r['decision']=='uncertain' for r in judged) if judged is not None else None,
            'quality_errors_observed':sum(r['decision']=='error' for r in judged) if judged is not None else None}

def compare(baseline,specialized):
    a,b=metrics(baseline),metrics(specialized)
    if a['scope_sha256']!=b['scope_sha256']:raise ValueError('Pregunta o hipótesis diferentes: no es una comparación controlada.')
    return {'baseline':a,'specialized':b,'limitations':[
        'Los veredictos y pasajes registrados no demuestran calidad científica.',
        'Sin revisión independiente, errores de contenido son desconocidos.',
        'Las llamadas son sólo las registradas; no se infiere cero para ejecuciones antiguas sin recibos.',
        'Tiempo es suma de llamadas registradas, no duración total del expediente.',
        'No atribuir diferencias a especialización sin controlar proveedor, documentos y condiciones.']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--specialized',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=compare(json.loads(args.baseline.read_text(encoding='utf-8')),json.loads(args.specialized.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Comparación de registros guardada. No se llamó al proveedor.')
