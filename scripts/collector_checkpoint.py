"""Validated Collector checkpoints, never verdicts or partial provider output."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import uuid

POLICY='collector-checkpoint-v1'
MAX_AGE_SECONDS=6*60*60

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()

def location(intel,key):return Path(intel)/'collector-checkpoints'/f'{key}.json'

def store(intel,key,result,run_id,dependencies):
    record={'policy':POLICY,'key':key,'created_at':dt.datetime.now(dt.timezone.utc).isoformat(),
            'run_id':run_id,'result':result,'result_sha256':digest(result),'dependencies':dependencies}
    path=location(intel,key);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)
    return record

def read(intel,key,current_dependencies):
    path=location(intel,key)
    if not path.exists():return None,'No hay recopilación completa guardada para estas entradas.'
    try:
        record=json.loads(path.read_text(encoding='utf-8'))
        age=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(record['created_at'])).total_seconds()
        if record['policy']!=POLICY or record['key']!=key or not 0<=age<=MAX_AGE_SECONDS:
            return None,'La recopilación guardada caducó o cambió su versión.'
        if digest(record['result'])!=record['result_sha256']:
            return None,'La recopilación guardada cambió; se volverá a buscar.'
        if current_dependencies(record['result'])!=record['dependencies']:
            return None,'Cambió un archivo o documento utilizado; se volverá a buscar.'
        return record,None
    except (ValueError,KeyError,TypeError,OSError):
        return None,'No se pudo validar la recopilación guardada; se volverá a buscar.'
