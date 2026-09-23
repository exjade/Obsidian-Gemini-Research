"""Explicit, identifier-only bibliographic metadata resolution.

Catalogue rendering never calls this module's network transport. Resolving is
an explicit CLI operation; persisted receipts are integrity-checked and can
be reused offline by library.refresh().
"""
import argparse
import datetime as dt
import hashlib
import http.client
import json
from pathlib import Path
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid

import source_identity
import source_metadata

ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = '.project-intelligence/source-resolutions'
POLICY = source_metadata.RESOLUTION_POLICY
MAX_BYTES = 1024 * 1024
TIMEOUT_SECONDS = 8
USER_AGENT = 'ObsidianGeminiResearch/1.0 (bibliographic metadata resolver)'
ALLOWED_HOSTS = {'api.crossref.org', 'eutils.ncbi.nlm.nih.gov', 'www.ncbi.nlm.nih.gov'}
PROVIDERS = {
    'doi': ('crossref', 'doi'),
    'pmid': ('ncbi', 'pmid'),
    'pmcid': ('ncbi', 'pmcid'),
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise ValueError('El proveedor bibliográfico intentó redirigir la solicitud')


def _allowed_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS
            or parsed.port not in (None, 443) or parsed.username or parsed.password
            or parsed.fragment):
        raise ValueError('Destino fuera de la lista de proveedores permitidos')
    return parsed


def fetch(url, timeout=TIMEOUT_SECONDS):
    """Fetch one fixed-provider API URL, rejecting redirects and large bodies."""
    _allowed_url(url)
    request = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
        'Accept-Encoding': 'identity',
    })
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(
        context=ssl.create_default_context()))
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            raise ValueError('El proveedor bibliográfico intentó redirigir la solicitud') from exc
        body = exc.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError('Respuesta bibliográfica mayor que el límite permitido') from exc
        return {'status': exc.code, 'url': exc.geturl(), 'body': body}
    with response:
        if response.geturl() != url:
            raise ValueError('La dirección del proveedor cambió durante la consulta')
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError('Respuesta bibliográfica mayor que el límite permitido')
        return {'status': response.status, 'url': response.geturl(), 'body': body}


def _crossref_url(doi):
    return 'https://api.crossref.org/works/' + urllib.parse.quote(doi, safe='')


def _ncbi_summary_url(pmid):
    query = urllib.parse.urlencode({'db': 'pubmed', 'id': pmid, 'retmode': 'json'})
    return 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?' + query


def _ncbi_pmcid_url(pmcid):
    query = urllib.parse.urlencode({'ids': pmcid, 'format': 'json'})
    return 'https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?' + query


def _request_json(url, transport):
    _allowed_url(url)
    response = transport(url)
    if not isinstance(response, dict):
        raise ValueError('Respuesta de transporte inválida')
    if response.get('status') == 404:
        return None, response.get('body', b'')
    if response.get('status') != 200:
        raise ValueError('El proveedor bibliográfico respondió HTTP ' + str(response.get('status')))
    if response.get('url') != url:
        raise ValueError('La respuesta no procede de la URL bibliográfica solicitada')
    body = response.get('body', b'')
    if not isinstance(body, bytes) or len(body) > MAX_BYTES:
        raise ValueError('Respuesta bibliográfica inválida o demasiado grande')
    try:
        return json.loads(body.decode('utf-8')), body
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('El proveedor devolvió JSON inválido') from exc


def _field(metadata, field, raw):
    if not isinstance(raw, str) or not raw.strip():
        return
    if field in ('doi', 'pmid', 'pmcid'):
        normalized = source_metadata.normalize_identifier(field, raw)
    elif field == 'title':
        normalized = ' '.join(raw.split())[:2000]
        raw = raw[:2000]
    elif field == 'url':
        normalized = source_metadata.normalize_url(raw)
    else:
        return
    if normalized:
        metadata[field] = {'raw': raw[:2000], 'normalized': normalized}


def _resolve_crossref(value, transport):
    url = _crossref_url(value)
    payload, body = _request_json(url, transport)
    if payload is None:
        return 'not_found', {}, body, url
    message = payload.get('message') if isinstance(payload, dict) else None
    if not isinstance(message, dict):
        raise ValueError('Respuesta Crossref sin registro bibliográfico')
    metadata = {}
    _field(metadata, 'doi', message.get('DOI'))
    title = message.get('title')
    if isinstance(title, list) and title:
        _field(metadata, 'title', title[0])
    _field(metadata, 'url', message.get('URL'))
    found_doi = metadata.get('doi', {}).get('normalized', '')
    if found_doi != value:
        return 'conflict', metadata, body, url
    return ('resolved' if metadata else 'not_found'), metadata, body, url


def _summary_metadata(pmid, payload, metadata):
    result = payload.get('result', {}) if isinstance(payload, dict) else {}
    item = result.get(pmid) if isinstance(result, dict) else None
    if not isinstance(item, dict) or str(item.get('uid', pmid)) != pmid:
        return False
    _field(metadata, 'pmid', str(item.get('uid', pmid)))
    _field(metadata, 'title', item.get('title'))
    for article in item.get('articleids', []):
        if not isinstance(article, dict):
            continue
        kind = str(article.get('idtype', '')).casefold()
        if kind in ('doi', 'pmc', 'pmcid'):
            _field(metadata, 'pmcid' if kind in ('pmc', 'pmcid') else 'doi',
                   str(article.get('value', '')))
    return True


def _resolve_pmid(value, transport):
    url = _ncbi_summary_url(value)
    payload, body = _request_json(url, transport)
    if payload is None:
        return 'not_found', {}, body, url
    metadata = {}
    if not _summary_metadata(value, payload, metadata):
        return 'not_found', {}, body, url
    found = metadata.get('pmid', {}).get('normalized', '')
    return ('resolved' if found == value and metadata else 'conflict'), metadata, body, url


def _resolve_pmcid(value, transport):
    url = _ncbi_pmcid_url(value)
    payload, body = _request_json(url, transport)
    if payload is None:
        return 'not_found', {}, body, url
    records = payload.get('records', []) if isinstance(payload, dict) else []
    match = next((r for r in records if isinstance(r, dict)
                  and source_metadata.normalize_identifier('pmcid', str(r.get('pmcid', ''))) == value), None)
    if not match or match.get('errmsg'):
        return 'not_found', {}, body, url
    metadata = {}
    _field(metadata, 'pmcid', str(match.get('pmcid', '')))
    _field(metadata, 'pmid', str(match.get('pmid', '')))
    _field(metadata, 'doi', str(match.get('doi', '')))
    if metadata.get('pmid', {}).get('normalized'):
        summary_url = _ncbi_summary_url(metadata['pmid']['normalized'])
        summary, summary_body = _request_json(summary_url, transport)
        body += b'\n' + summary_body
        if summary is not None:
            _summary_metadata(metadata['pmid']['normalized'], summary, metadata)
    return ('resolved' if metadata.get('pmcid', {}).get('normalized') == value else 'conflict'), metadata, body, url


def resolve(field, value, transport=fetch):
    """Return a provenance-rich receipt without writing it to disk."""
    if field not in PROVIDERS:
        raise ValueError('Campo bibliográfico no admitido; usa DOI, PMID o PMCID')
    normalized = source_metadata.normalize_identifier(field, value)
    if not normalized:
        raise ValueError('Identificador bibliográfico inválido')
    provider, _ = PROVIDERS[field]
    receipt = {
        'policy': POLICY,
        'provider': provider,
        'lookup_field': field,
        'lookup_raw': str(value)[:500],
        'lookup_value': normalized,
        'retrieved_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'outcome': 'error',
        'metadata': {},
    }
    try:
        if field == 'doi':
            outcome, metadata, body, url = _resolve_crossref(normalized, transport)
        elif field == 'pmid':
            outcome, metadata, body, url = _resolve_pmid(normalized, transport)
        else:
            outcome, metadata, body, url = _resolve_pmcid(normalized, transport)
        receipt.update(outcome=outcome, metadata=metadata, endpoint=url,
                       response_sha256=hashlib.sha256(body).hexdigest())
    except (OSError, ValueError, TimeoutError, http.client.HTTPException, urllib.error.URLError) as exc:
        receipt['error'] = (type(exc).__name__ + ': ' + str(exc))[:500]
    return receipt


def _receipt_id(source_id, provider, field, value):
    raw = '\n'.join((source_id, provider, field, value))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _receipt_payload(receipt):
    return {key: value for key, value in receipt.items() if key != 'integrity_sha256'}


def seal(receipt):
    payload = json.dumps(_receipt_payload(receipt), sort_keys=True, ensure_ascii=False,
                         separators=(',', ':')).encode('utf-8')
    return {**receipt, 'integrity_sha256': hashlib.sha256(payload).hexdigest()}


def valid_receipt(receipt, source_id=None):
    if not isinstance(receipt, dict) or receipt.get('policy') != POLICY:
        return False
    if source_id is not None and receipt.get('source_id') != source_id:
        return False
    provider = receipt.get('provider')
    field = receipt.get('lookup_field')
    value = receipt.get('lookup_value')
    if field not in PROVIDERS or PROVIDERS[field][0] != provider:
        return False
    if source_metadata.normalize_identifier(field, value) != value:
        return False
    if receipt.get('outcome') not in ('resolved', 'not_found', 'conflict', 'error'):
        return False
    expected_id = _receipt_id(str(receipt.get('source_id', '')), provider, field, value)
    if receipt.get('id') != expected_id:
        return False
    try:
        return seal(receipt).get('integrity_sha256') == receipt.get('integrity_sha256')
    except (TypeError, ValueError):
        return False


def save_receipt(root, source_id, receipt):
    if not re.fullmatch(r'[0-9a-f]{64}', source_id or ''):
        raise ValueError('source_id inválido')
    receipt = dict(receipt)
    receipt['source_id'] = source_id
    receipt['id'] = _receipt_id(source_id, receipt['provider'], receipt['lookup_field'], receipt['lookup_value'])
    sealed = seal(receipt)
    directory = Path(root) / DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (sealed['id'] + '.json')
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(sealed, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)
    return sealed


def trusted_receipts_for_source(root, source_id):
    directory = Path(root) / DIRECTORY
    if not directory.exists():
        return []
    receipts = []
    for path in sorted(directory.glob('*.json')):
        try:
            receipt = json.loads(path.read_text(encoding='utf-8'))
            if path.stem == receipt.get('id') and valid_receipt(receipt, source_id):
                receipts.append(receipt)
        except (OSError, ValueError, TypeError):
            continue
    return receipts


def _catalog_source(root, source_id):
    if not re.fullmatch(r'[0-9a-f]{64}', source_id or ''):
        raise ValueError('source_id inválido')
    catalogue = json.loads((Path(root) / '.project-intelligence/library/sources.json').read_text(encoding='utf-8'))
    source = next((item for item in catalogue.get('sources', []) if item.get('source_id') == source_id), None)
    if not source or source.get('identity_policy') != source_identity.POLICY:
        raise ValueError('La fuente no está en el catálogo canónico')
    return source


def resolve_for_source(root, source_id, field, value, force=False, transport=fetch):
    """Resolve only a declared/observed identifier on an existing catalogue source."""
    source = _catalog_source(root, source_id)
    normalized = source_metadata.normalize_identifier(field, value)
    if not normalized:
        raise ValueError('Identificador bibliográfico inválido')
    known = source.get('metadata', {}).get('fields', {}).get(field, {}).get('values', [])
    if normalized not in {source_metadata.normalize_identifier(field, item) for item in known}:
        raise ValueError('El identificador no aparece ya registrado para esta fuente')
    provider = PROVIDERS[field][0]
    prior = next((item for item in trusted_receipts_for_source(root, source_id)
                  if item.get('provider') == provider and item.get('lookup_field') == field
                  and item.get('lookup_value') == normalized), None)
    if prior and not force:
        return prior
    receipt = resolve(field, value, transport)
    return save_receipt(root, source_id, receipt)


def _main(argv=None):
    parser = argparse.ArgumentParser(description='Resolver metadatos bibliográficos por identificador ya catalogado')
    parser.add_argument('--root', type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument('--source-id', required=True, help='source_id SHA-256 ya presente en sources.json')
    parser.add_argument('--field', required=True, choices=tuple(PROVIDERS), help='doi, pmid o pmcid')
    parser.add_argument('--identifier', required=True, help='Identificador ya registrado en el catálogo')
    parser.add_argument('--refresh', action='store_true', help='Repetir explícitamente una resolución guardada')
    args = parser.parse_args(argv)
    receipt = resolve_for_source(args.root, args.source_id, args.field, args.identifier, args.refresh)
    print(json.dumps({'id': receipt['id'], 'outcome': receipt['outcome'], 'provider': receipt['provider'],
                      'path': str(Path(args.root) / DIRECTORY / (receipt['id'] + '.json'))}, ensure_ascii=False))
    return 0 if receipt['outcome'] in ('resolved', 'not_found', 'conflict') else 1


if __name__ == '__main__':
    raise SystemExit(_main())
