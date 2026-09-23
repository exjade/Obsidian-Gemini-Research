"""Bounded cross-case candidates; Collector and Skeptic must reassess relevance."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path
import source_identity

POLICY='cross-case-candidates-v1'
STOP={'para','como','with','from','that','this','which','entre','sobre','mayor','mejor','frente','adultos','informacion','information','learning','aprendizaje'}

def terms(text):
    normalized=unicodedata.normalize('NFKD',text.casefold())
    normalized=''.join(c for c in normalized if not unicodedata.combining(c))
    return {w for w in re.findall(r'\w+',normalized) if len(w)>3 and w not in STOP}

def candidates(root, pending, limit=6):
    if limit<1:return []
    base=Path(root)/'.project-intelligence/library'
    targets={c.get('investigation_id') for c in pending}
    queries={c['id']:terms(c['claim']) for c in pending}
    found=[]
    if not base.is_dir():return []
    for folder in sorted(base.iterdir())[:200]:
        if not folder.is_dir() or folder.is_symlink() or folder.name in targets:continue
        path=folder/'claims.json'
        try:
            if path.stat().st_size>2*1024*1024:continue
            rows=json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(rows,list):continue
        except (OSError,ValueError):continue
        for claim in rows[:100]:
            if not isinstance(claim,dict):continue
            evidence_rows=claim.get('evidence',[])
            if not isinstance(evidence_rows,list):continue
            claim_text=claim.get('claim','')
            if not isinstance(claim_text,str):claim_text=''
            for index,evidence in enumerate(evidence_rows[:30]):
                # Local PDFs require explicit target-case authorization; not shared here.
                if not isinstance(evidence,dict) or evidence.get('type')!='external':continue
                url=evidence.get('url');excerpt=evidence.get('excerpt')
                if not isinstance(url,str) or not re.match(r'^https?://[^\s]+$',url):continue
                if not isinstance(excerpt,str) or not excerpt or len(excerpt)>10000:continue
                words=terms(claim_text+' '+excerpt)
                for target,query in queries.items():
                    overlap=query & words
                    if len(overlap)<2:continue
                    canonical=source_identity.has_catalog_identity(evidence)
                    digest=hashlib.sha256(json.dumps({'case':folder.name,'claim':claim.get('id'),'index':index,'url':url,'excerpt':excerpt},sort_keys=True).encode()).hexdigest()
                    found.append({'candidate_id':digest,'target_claim_id':target,'origin_case_id':folder.name,
                                  'origin_claim_id':claim.get('id'),'origin_evidence_index':index,
                                  'source_id':evidence.get('source_id') if canonical else None,'evidence_id':evidence.get('evidence_id') if canonical else None,
                                  'identity_policy':evidence.get('source_identity_policy') if canonical else None,
                                  'url':url,'excerpt':excerpt,'title':evidence.get('title',''),
                                  'declared_relation':evidence.get('relation','unreviewed'),
                                  'relation_provenance':'origin_claim_passage' if canonical else 'legacy_url_excerpt_noncanonical',
                                  'retrieval':'lexical_candidate','matched_terms':sorted(overlap),
                                  'relevance_review':'pending','score':len(overlap)/max(1,len(query))})
    found.sort(key=lambda x:(-x['score'],x['candidate_id']))
    result=[];seen=set()
    for row in found:
        key=(row['target_claim_id'],row['url'],row['excerpt'])
        if key in seen:continue
        seen.add(key);result.append(row)
        if len(result)>=limit:break
    return result

def selected_origins(evidence, target_claim_id, proposals):
    return [{k:row.get(k) for k in ('candidate_id','origin_case_id','origin_claim_id','origin_evidence_index','source_id','evidence_id','identity_policy','relation_provenance','declared_relation')}
            for row in proposals if row['target_claim_id']==target_claim_id
            and ((evidence.get('source_id') and row.get('source_id')==evidence.get('source_id') and row.get('evidence_id')==evidence.get('evidence_id'))
                 or (not evidence.get('source_id') and not row.get('source_id') and row['url']==evidence.get('url') and row['excerpt']==evidence.get('excerpt')))]

def apply_review(evidence,claim_id):
    relevance=evidence.get('reuse_relevance')
    if (not isinstance(relevance,dict) or relevance.get('target_claim_id')!=claim_id
        or relevance.get('decision') not in ('support','contradiction','context','not_relevant')
        or any(not isinstance(relevance.get(k),str) or not relevance[k].strip() for k in ('reason','limits'))):
        raise ValueError('PASS 3: falta revisión de pertinencia del pasaje reutilizado para esta afirmación.')
    evidence['relation']='context' if relevance['decision']=='not_relevant' else relevance['decision']
