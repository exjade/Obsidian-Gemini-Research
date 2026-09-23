"""Private document versions, bounded retrieval and independently checked citations."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
import uuid
import library

ENGINES = ('pypdf', 'docling-native', 'docling-standard')
DOCUMENT_KINDS=('original_research','review','law','regulation','jurisprudence','official_documentation','other')


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).split())


def base(root):
    return Path(root) / '.project-intelligence/documents'


def folder(root, ident):
    if not re.fullmatch('[0-9a-f]{64}', ident or ''):
        raise ValueError('Documento inválido')
    return base(root) / ident


def records(root, case_id):
    meta = library.read(library.case_path(case_id) / 'case.json')
    if not meta:
        raise ValueError('Expediente inexistente')
    result=[]
    for ident in meta.get('document_ids', []):
        record=library.read(folder(root,ident)/'metadata.json')
        if record:
            result.append({**record,'imports':[i for i in record['imports'] if i['case_id']==case_id],
                           'identity_reviews':[i for i in record.get('identity_reviews',[]) if i['case_id']==case_id]})
    return result


def authorized(root, case_id, ident):
    meta = library.read(library.case_path(case_id) / 'case.json', {})
    if ident not in meta.get('document_ids', []):
        raise ValueError('El documento no pertenece a este expediente')
    record = library.read(folder(root, ident) / 'metadata.json')
    if not record:
        raise ValueError('Documento no encontrado')
    return record


def import_pdf(root, case_id, raw, name, origin='', doi='', claim_id=None, engine='pypdf'):
    if engine not in ENGINES:
        raise ValueError('Extractor inválido')
    meta_path = library.case_path(case_id) / 'case.json'
    meta = library.read(meta_path)
    if not meta:
        raise ValueError('Expediente inexistente')
    if claim_id and not any(c['id'] == claim_id for c in library.read(meta_path.with_name('claims.json'), [])):
        raise ValueError('Afirmación inexistente')
    if not raw.startswith(b'%PDF-') or not 1 <= len(raw) <= 50 * 1024 * 1024:
        raise ValueError('Aporta un PDF de hasta 50 MB')
    if origin and not re.fullmatch(r'https?://[^\s]+', origin):
        raise ValueError('El origen debe ser una URL; no se descargará automáticamente')
    if doi and not re.fullmatch(r'10\.\d{4,9}/\S+', doi):
        raise ValueError('DOI inválido')
    ident = digest(raw); target = folder(root, ident)
    target.mkdir(parents=True, exist_ok=True)
    original = target / 'original.pdf'
    if original.exists():
        if digest(original.read_bytes()) != ident:
            raise ValueError('La copia conservada cambió; no se sobrescribió')
    else:
        original.write_bytes(raw)
    record = library.read(target / 'metadata.json', {'id': ident, 'sha256': ident,
                          'size': len(raw), 'imports': [], 'extractions': []})
    name = Path(name.replace('\\', '/')).name[:160]
    record['imports'].append({'case_id': case_id, 'claim_id': claim_id,
             'filename': name, 'origin_declared': origin, 'doi_declared': doi,
             'imported_at': stamp(), 'provenance': 'user-supplied-unconfirmed'})
    library.save(target / 'metadata.json', record)
    meta['document_ids'] = list(dict.fromkeys([*meta.get('document_ids', []), ident]))
    library.save(meta_path, meta)
    return ident


def python_runtime(root):
    configured = os.environ.get('DOCUMENTS_PYTHON')
    if configured:
        return configured
    candidate = Path(root) / '.venv-documents' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    return str(candidate) if candidate.exists() else sys.executable


def extract(root, ident, engine='pypdf', force=False):
    target = folder(root, ident); record = library.read(target / 'metadata.json')
    if not record:
        raise ValueError('Documento inexistente')
    if engine not in ENGINES:
        raise ValueError('Extractor inválido')
    if digest((target / 'original.pdf').read_bytes()) != ident:
        raise ValueError('El PDF conservado cambió')
    if not force:
        found = next((e for e in reversed(record['extractions']) if e['engine'] == engine and e['status'] == 'ready'), None)
        if found:
            extraction_data(root,ident,found['id'])
            return found
    xid = uuid.uuid4().hex; out = target / 'extractions' / xid
    out.mkdir(parents=True)
    entry = {'id': xid, 'engine': engine, 'status': 'running', 'started_at': stamp()}
    record['extractions'].append(entry); library.save(target / 'metadata.json', record)
    try:
        process = subprocess.run([python_runtime(root), str(Path(root) / 'scripts/document_worker.py'),
                       str(target / 'original.pdf'), str(out / 'document.json'), '--engine', engine],
                       capture_output=True, timeout=660, env={**os.environ, 'PYTHONUTF8': '1',
                               'HF_HUB_DISABLE_IMPLICIT_TOKEN':'1'})
        (out / 'stderr.log').write_bytes(process.stderr)
        if process.returncode:
            raise ValueError('No se pudo extraer el PDF: ' + process.stderr.decode('utf-8', errors='replace')[-2500:])
        if (out / 'document.json').stat().st_size > 20 * 1024 * 1024:
            raise ValueError('Texto extraído demasiado grande')
        data = library.read(out / 'document.json')
        chunks = []
        for page in data['pages']:
            text = page['text']
            for offset in range(0, len(text), 1000):
                passage = text[offset:offset + 1200]
                if not passage.strip():
                    continue
                chunks.append({'id': digest(f'{xid}:{page["physical_page"]}:{offset}'.encode()),
                               'physical_page': page['physical_page'], 'offset': offset,
                               'text': passage, 'text_sha256': digest(passage.encode())})
        if not chunks:
            raise ValueError('No hay texto recuperable. Este archivo puede necesitar OCR, todavía pendiente.')
        library.save(out / 'chunks.json', chunks)
        entry.update(status='ready', finished_at=stamp(), pages=len(data['pages']),
                     text_pages=sum(bool(p['text'].strip()) for p in data['pages']),
                     chunks=len(chunks), version=data['version'], ocr=data['ocr'],
                     seconds=data['seconds'], peak_rss_bytes=data.get('peak_rss_bytes'),
                     tables_detected=data.get('tables_detected', 0),
                     data_sha256=digest((out / 'document.json').read_bytes()),
                     chunks_sha256=digest((out / 'chunks.json').read_bytes()))
        record['title_declared_in_pdf'] = data['metadata_declared_in_pdf'].get('/Title', '')
        record['active_extraction'] = xid
    except Exception as exc:
        entry.update(status='error', finished_at=stamp(), error=str(exc))
        raise
    finally:
        library.save(target / 'metadata.json', record)
    return entry


def extraction_data(root, ident, xid):
    if not re.fullmatch('[0-9a-f]{32}', xid or ''):
        raise ValueError('Extracción inválida')
    target = folder(root, ident); record = library.read(target / 'metadata.json', {})
    entry = next((e for e in record.get('extractions', []) if e['id'] == xid and e['status'] == 'ready'), None)
    if not entry:
        raise ValueError('Extracción no disponible')
    out = target / 'extractions' / xid
    for name, key in [('chunks.json', 'chunks_sha256'), ('document.json', 'data_sha256')]:
        if digest((out / name).read_bytes()) != entry[key]:
            raise ValueError('La extracción conservada cambió')
    return library.read(out / 'document.json'), library.read(out / 'chunks.json')


def retrieve(root, case_id, query, claim_id=None, limit=8, document_ids=None):
    synonyms = {'memoria': 'memory', 'aprendizaje': 'learning', 'esquemas': 'schema',
                'capacidad': 'capacity', 'problemas': 'problem', 'guiada': 'guidance',
                'recuperación': 'retrieval', 'atención': 'attention', 'inteligencia': 'intelligence'}
    words = set(re.findall(r'\w{4,}', query.casefold()))
    words.update(synonyms[w] for w in list(words) if w in synonyms)
    ranked = []
    permitted=set(document_ids or [])
    for record in records(root, case_id):
        if permitted and record['id'] not in permitted:
            continue
        imports = [i for i in record['imports'] if i['case_id'] == case_id and i.get('claim_id') in (None, claim_id)]
        if not imports or not record.get('active_extraction'):
            continue
        xid = record['active_extraction']
        _, chunks = extraction_data(root, record['id'], xid)
        for chunk in chunks:
            score = sum(word in chunk['text'].casefold() for word in words)
            if not score:
                continue
            ranked.append((score, {**chunk, 'document_id': record['id'], 'extraction_id': xid,
                   'document_sha256': record['sha256'], 'title': record.get('title_declared_in_pdf', ''),
                   'origin_declared': imports[-1]['origin_declared'], 'doi_declared': imports[-1]['doi_declared'],
                   'retrieval_method': 'lexical', 'query': query, 'relation': 'unreviewed'}))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    chosen=[]; per_document={}
    document_count=len({chunk['document_id'] for _,chunk in ranked})
    for score,chunk in ranked:
        ident=chunk['document_id']
        if per_document.get(ident,0)>=max(1,limit//max(1,document_count)):continue
        chosen.append(chunk);per_document[ident]=per_document.get(ident,0)+1
        if len(chosen)==limit:break
    return chosen


def validate(root, evidence, case_id):
    if not case_id:
        raise ValueError('La evidencia PDF necesita un expediente')
    ident = evidence.get('document_id'); record = authorized(root, case_id, ident)
    if evidence.get('document_sha256') != ident or digest((folder(root, ident) / 'original.pdf').read_bytes()) != ident:
        raise ValueError('La identidad del PDF no coincide')
    _, chunks = extraction_data(root, ident, evidence.get('extraction_id'))
    chunk = next((c for c in chunks if c['id'] == evidence.get('chunk_id')), None)
    if not chunk or type(evidence.get('physical_page')) is not int or evidence['physical_page'] != chunk['physical_page']:
        raise ValueError('Pasaje o página PDF inexistente')
    excerpt = evidence.get('excerpt', '')
    if not isinstance(excerpt, str) or len(normalized(excerpt)) < 40 or normalized(excerpt) not in normalized(chunk['text']):
        raise ValueError('El extracto no coincide con el pasaje PDF conservado')
    return {'eligible': True, 'document_id': ident, 'physical_page': chunk['physical_page'],
            'excerpt_match': True, 'semantic_support_reviewed': False}


def review_identity(root,case_id,ident,actor,kind,origin,doi,notes,decision='confirmed'):
    record=authorized(root,case_id,ident)
    if kind not in DOCUMENT_KINDS or decision not in ('confirmed','rejected'):
        raise ValueError('Clasificación de documento inválida')
    if not actor.strip() or not notes.strip() or not re.fullmatch(r'https?://[^\s]+',origin):
        raise ValueError('Registra quién revisó, qué comprobó y el enlace editorial/institucional')
    if doi and not re.fullmatch(r'10\.\d{4,9}/\S+',doi):raise ValueError('DOI inválido')
    review={'id':uuid.uuid4().hex,'case_id':case_id,'reviewed_at':stamp(),'actor':actor[:120],
            'document_kind':kind,'origin':origin,'doi':doi,'notes':notes[:4000],'decision':decision,
            'scope':'publication identity only; not claim truth'}
    record.setdefault('identity_reviews',[]).append(review)
    library.save(folder(root,ident)/'metadata.json',record)
    return review


def identity_review(root,case_id,ident):
    record=authorized(root,case_id,ident)
    reviews=[r for r in record.get('identity_reviews',[]) if r['case_id']==case_id]
    return reviews[-1] if reviews and reviews[-1]['decision']=='confirmed' else None


def identity_key(root,case_id,evidence):
    if evidence['type']=='document':
        review=identity_review(root,case_id,evidence['document_id'])
        doi=(review or {}).get('doi')
        return ('doi',doi.casefold()) if doi else ('document',evidence['document_id'])
    if evidence['type']=='external':
        url=evidence['url'];doi=evidence.get('doi')
        if not doi:
            match=re.search(r'(10\.\d{4,9}/[^?#\s]+)',url)
            if match:doi=match[1]
        if not doi and case_id:
            for doc in records(root,case_id):
                if any(i['origin_declared'].rstrip('/')==url.rstrip('/') for i in doc['imports']):
                    review=identity_review(root,case_id,doc['id']);doi=(review or {}).get('doi')
                    if doi:break
        if doi:return ('doi',doi.casefold())
    return None


def report(root, case_id):
    text = '# Documentos locales\n\nTexto recuperado no significa afirmación comprobada. Los datos de procedencia siguen siendo declaraciones de adquisición.\n\n'
    for record in records(root, case_id):
        acquired = [i for i in record['imports'] if i['case_id'] == case_id][-1]
        text += '## ' + acquired['filename'] + '\n\n'
        text += 'SHA-256: `' + record['id'] + '`\n\nOrigen declarado: ' + (acquired['origin_declared'] or 'no registrado') + '\n\n'
        text += 'Copia: [abrir PDF](adjuntos/documento-' + record['id'] + '.pdf)\n\n'
        for review in record.get('identity_reviews',[]):
            text+=f'Revisión de identidad: {review["decision"]}; {review["actor"]}; {review["reviewed_at"]}. Tipo: {review["document_kind"]}. No verifica afirmaciones.\n\n'
        for e in record['extractions']:
            text += f'- {e["engine"]}: {e["status"]}; páginas: {e.get("pages", "pendientes")}; OCR: no.\n'
            if e.get('error'):
                text += '  Error: ' + e['error'][:500] + '\n'
        target = library.case_path(case_id) / 'adjuntos' / ('documento-' + record['id'] + '.pdf')
        if target.exists() and digest(target.read_bytes()) != record['id']:
            raise ValueError('La copia del expediente fue modificada; se conserva sin sobrescribir')
        if not target.exists():
            target.parent.mkdir(exist_ok=True); target.write_bytes((folder(root, record['id']) / 'original.pdf').read_bytes())
    library.write(library.case_path(case_id) / 'documentos.md', text)
    return text
