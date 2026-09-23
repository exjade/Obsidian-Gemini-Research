"""Deterministic, local-only metadata consolidation for catalogued sources."""
import re
from urllib.parse import urlsplit, urlunsplit

import source_identity

POLICY = 'source-metadata-v1'
RESOLUTION_POLICY = 'source-metadata-resolution-v1'
FIELDS = ('title', 'doi', 'pmid', 'pmcid', 'url', 'original_url', 'final_url',
          'normalized_final_url', 'content_type', 'document_sha256', 'snapshot_sha256', 'source_type')


def normalize_doi(value):
    value = str(value or '').strip()
    value = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)', '', value, flags=re.I)
    value = value.strip().rstrip('.,;')
    return value.casefold() if re.fullmatch(r'10\.\d{4,9}/\S+', value, re.I) else ''


def normalize_identifier(field, value):
    value = str(value or '').strip()
    if field == 'doi':
        return normalize_doi(value)
    if field == 'pmid':
        value = re.sub(r'^(?:pmid\s*:\s*)', '', value, flags=re.I)
        return value if re.fullmatch(r'\d+', value) else ''
    if field == 'pmcid':
        value = re.sub(r'^(?:pmcid\s*:\s*)', '', value, flags=re.I)
        return value.upper() if re.fullmatch(r'PMC\d+', value, re.I) else ''
    return ''


def normalize_url(value):
    value = str(value or '').strip()
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            return ''
        scheme = parts.scheme.lower()
        host = parts.hostname.lower()
        if ':' in host and not host.startswith('['):
            host = '[' + host + ']'
        port = parts.port
        if port and not (scheme == 'https' and port == 443 or scheme == 'http' and port == 80):
            host += ':' + str(port)
        return urlunsplit((scheme, host, parts.path or '/', parts.query, ''))
    except ValueError:
        return ''


def normalize_canonical_url(value):
    """Validate the scheme-less form emitted by source_identity.canonical_url."""
    value = str(value or '').strip()
    if not value or '://' in value:
        return ''
    try:
        parsed = urlsplit('https://' + value)
        if not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            return ''
        normalized = source_identity.canonical_url('https://' + value)
        return value if normalized == value else ''
    except ValueError:
        return ''


def assertion(field, value, provenance, status='observed', timestamp='', reference=''):
    if field not in FIELDS or value in (None, '') or status not in ('observed', 'declared', 'reviewed'):
        return None
    value = str(value).strip()
    if not value:
        return None
    if field in ('doi', 'pmid', 'pmcid'):
        value = normalize_identifier(field, value)
        if not value:
            return None
    elif field in ('url', 'original_url', 'final_url', 'normalized_final_url'):
        value = normalize_canonical_url(value) if field == 'normalized_final_url' else normalize_url(value)
        if not value:
            return None
    elif field == 'document_sha256':
        value = value.lower()
        if not re.fullmatch(r'[0-9a-f]{64}', value):
            return None
    return {'field': field, 'value': value, 'provenance': str(provenance), 'status': status,
            **({'timestamp': str(timestamp)} if timestamp else {}),
            **({'reference': str(reference)} if reference else {})}


def consolidate(assertions):
    """Keep all attributable claims; surface disagreements without choosing a winner."""
    clean = []
    seen = set()
    for item in assertions:
        if not isinstance(item, dict):
            continue
        candidate = assertion(item.get('field'), item.get('value'), item.get('provenance', ''),
                              item.get('status', 'observed'), item.get('timestamp', ''), item.get('reference', ''))
        if not candidate:
            continue
        raw_value = item.get('raw_value')
        if isinstance(raw_value, str) and raw_value:
            candidate['raw_value'] = raw_value[:2000]
        key = tuple((k, candidate.get(k, '')) for k in ('field', 'value', 'provenance', 'status', 'timestamp', 'reference', 'raw_value'))
        if key not in seen:
            clean.append(candidate); seen.add(key)
    clean.sort(key=lambda x: (x['field'], x['value'], x['provenance'], x['status'], x.get('timestamp', ''), x.get('reference', ''), x.get('raw_value', '')))
    fields = {}
    conflicts = []
    for field in FIELDS:
        items = [x for x in clean if x['field'] == field]
        if not items:
            continue
        values = sorted({x['value'] for x in items})
        fields[field] = {'value': values[0] if len(values) == 1 else None, 'values': values, 'assertions': items}
        if len(values) > 1 and not field.endswith('_url') and field != 'url':
            conflicts.append({'field': field, 'values': values, 'assertions': items})
    return {'policy': POLICY, 'fields': fields, 'conflicts': conflicts}


def resolution_assertions(receipt):
    """Convert a validated resolver receipt to attributed catalogue facts.

    The resolver receipt remains the provenance record. Only resolved receipts
    contribute assertions; conflicts and failed lookups remain visible without
    being treated as bibliographic facts.
    """
    if (not isinstance(receipt, dict) or receipt.get('policy') != RESOLUTION_POLICY
            or receipt.get('outcome') != 'resolved'
            or not isinstance(receipt.get('metadata'), dict)):
        return []
    provider = str(receipt.get('provider', ''))
    if provider not in ('crossref', 'ncbi'):
        return []
    timestamp = str(receipt.get('retrieved_at', ''))
    reference = str(receipt.get('id', ''))
    result = []
    for field, values in sorted(receipt['metadata'].items()):
        if not isinstance(values, dict):
            continue
        raw = values.get('raw')
        normalized = values.get('normalized')
        item = assertion(field, normalized,
                         f'resolver.{provider}.{receipt.get("lookup_field", "identifier")}',
                         'observed', timestamp, reference)
        if item:
            if isinstance(raw, str) and raw:
                item['raw_value'] = raw[:2000]
            result.append(item)
    return result
