"""Document identity signals. Identity never establishes authenticity or support."""
import hashlib
import json
import re
from urllib.parse import urlsplit,parse_qsl,urlencode,unquote

POLICY='source-identity-v1'
ASSESSMENT_POLICY='source-assessment-v1'
CATALOG_POLICY='source-catalog-v1'
RELATION_ROLES=('support','contradiction','context','unreviewed')
TRACKING={'fbclid','gclid','msclkid','mc_cid','mc_eid'}

def normalize_relation(value):
    """Normalize claim-passage role conservatively for catalogue display."""
    return value if value in RELATION_ROLES else 'unreviewed'

def has_catalog_identity(evidence):
    """Accept only IDs explicitly emitted by this policy in SHA-256 form."""
    return (isinstance(evidence,dict) and evidence.get('source_identity_policy')==POLICY
            and isinstance(evidence.get('source_id'),str) and re.fullmatch(r'[0-9a-f]{64}',evidence['source_id']) is not None
            and isinstance(evidence.get('evidence_id'),str) and re.fullmatch(r'[0-9a-f]{64}',evidence['evidence_id']) is not None)

def canonical_url(url):
    p=urlsplit(url)
    host=(p.hostname or '').lower()
    port=p.port
    if port and not (p.scheme=='https' and port==443 or p.scheme=='http' and port==80):host+=':'+str(port)
    query=sorted((k,v) for k,v in parse_qsl(p.query,keep_blank_values=True)
                 if not k.lower().startswith('utm_') and k.lower() not in TRACKING)
    return host+(p.path or '/').rstrip('/')+('?' + urlencode(query) if query else '')

def url_identifier(url):
    p=urlsplit(url);path=unquote(p.path).rstrip('/');host=(p.hostname or '').lower()
    if host in ('pubmed.ncbi.nlm.nih.gov','www.ncbi.nlm.nih.gov'):
        match=re.fullmatch(r'(?:/pubmed)?/(\d+)',path)
        if match:return 'pmid:'+match[1]
    if host in ('pmc.ncbi.nlm.nih.gov','www.ncbi.nlm.nih.gov'):
        match=re.fullmatch(r'/(?:pmc/)?articles/(PMC\d+)',path,re.I)
        if match:return 'pmcid:'+match[1].upper()
    match=re.search(r'(10\.\d{4,9}/[^\s?#]+)',path,re.I)
    if match:
        doi=match[1]
        if '/content/pdf/' in path and doi.lower().endswith('.pdf'):doi=doi[:-4]
        return 'doi:'+doi.casefold()
    return None

def identify(evidence,receipt=None,reviewed_key=None):
    signals=set();basis='reference_only';kind=evidence['type']
    if kind=='external':
        for url in {evidence['url'],(receipt or {}).get('final_url',evidence['url'])}:
            signals.add('url:'+canonical_url(url))
            identifier=url_identifier(url)
            if identifier:signals.add(identifier);basis='identifier_in_url'
        if receipt and receipt.get('eligible') and receipt.get('body_sha256'):
            signals.add('snapshot:'+receipt['body_sha256'])
    elif kind=='document':signals.add('document:'+evidence['document_sha256']);basis='local_bytes'
    elif kind=='file':signals.add('file:'+evidence['path'])
    elif kind=='commit':signals.add('commit:'+evidence['ref'].lower())
    if reviewed_key and kind=='document':
        signals.add(str(reviewed_key[0])+':'+str(reviewed_key[1]));basis='reviewed_document_identity'
    elif reviewed_key and kind=='external' and reviewed_key[0]=='doi':
        # Conservative duplicate signal only; a declared DOI cannot increase corroboration.
        signals.add('doi:'+str(reviewed_key[1]).casefold())
    preferred=next((s for prefix in ('doi:','pmid:','pmcid:','document:','file:','commit:','url:')
                    for s in sorted(signals) if s.startswith(prefix)),sorted(signals)[0])
    sid=hashlib.sha256(preferred.encode('utf-8')).hexdigest()
    passage={'source_id':sid,'excerpt':evidence.get('excerpt'),'page':evidence.get('physical_page'),
             'extraction_id':evidence.get('extraction_id'),'chunk_id':evidence.get('chunk_id'),'lines':evidence.get('lines')}
    eid=hashlib.sha256(json.dumps(passage,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()
    return {'policy':POLICY,'source_id':sid,'evidence_id':eid,'identity_key':preferred,
            'signals':sorted(signals),'basis':basis,'authenticity_confirmed':False,'semantic_support_confirmed':False}

def assess(evidence,receipt=None,reviewed_key=None,semantic_review=None):
    """Return separate, conservative dimensions; no dimension implies another."""
    identity=identify(evidence,receipt,reviewed_key)
    kind=evidence['type'];review=semantic_review or evidence.get('semantic_review') or {}
    decision=review.get('decision','unreviewed')
    if decision not in ('support','contradiction','context','insufficient','unreviewed'):
        decision='unreviewed'
    if evidence.get('primary') is True:
        primary_status='provider_declared_primary';primary_basis='provider_annotation_only'
    elif evidence.get('primary') is False:
        primary_status='provider_declared_non_primary';primary_basis='provider_annotation_only'
    else:
        primary_status='unreviewed';primary_basis='no_primary_review'
    access=('local' if kind in ('document','file','commit') else
            (receipt or {}).get('availability','unreviewed').casefold())
    return {
        'policy':ASSESSMENT_POLICY,
        'identity':{k:identity[k] for k in ('source_id','evidence_id','identity_key','signals','basis')},
        'primary':{'status':primary_status,'basis':primary_basis,
                   'provider_declared':evidence.get('primary') if isinstance(evidence.get('primary'),bool) else None,
                   'document_identity_reviewed':bool(kind=='document' and reviewed_key),
                   'document_identity_basis':'registered_document_identity_review'
                                             if kind=='document' and reviewed_key else 'not_applicable'},
        'independence':{'status':'not_established','basis':'no_duplicate_signal_is_not_proof_of_independence'},
        'authenticity':{'status':'not_confirmed','basis':'identity_signals_only'},
        'credibility':{'status':'unreviewed','basis':'not_inferred_from_access_or_identity'},
        'access':{'status':access,'basis':'local_material' if kind!='external' else 'technical_receipt'},
        'semantic_support':{'status':decision,'basis':review.get('basis','not_semantically_reviewed'),
                            'limits':review.get('limits','')},
    }

def independence_components(entries):
    """Explain the existing transitive collapse without claiming scientific independence."""
    components=[]
    for index,(identity,declared_group) in enumerate(entries):
        own=set(identity['signals'])
        declared='declared-group:'+declared_group.strip().casefold()
        signals=own|{declared};members=[index];source_ids=[identity['source_id']]
        overlaps=[c for c in components if set(c['signals']) & signals]
        for component in overlaps:
            signals.update(component['signals']);members.extend(component['members'])
            source_ids.extend(component['source_ids']);components.remove(component)
        components.append({'members':sorted(members),'source_ids':sorted(set(source_ids)),
                           'signals':sorted(signals),
                           'collapse_basis':sorted(s for s in signals if s in own or s==declared),
                           'scientific_independence':'not_established'})
    return components

def independent_count(entries):
    """Union duplicate signals AND declared groups, including transitive aliases."""
    return len(independence_components(entries))
