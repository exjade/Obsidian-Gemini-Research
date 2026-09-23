"""Explicit preview/apply migration for historical evidence identity IDs.

Planning writes an auditable manifest but never changes claims or evidence.
Applying is a separate CLI command and revalidates every candidate snapshot.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

import documents
import library
import source_check
import source_identity

ROOT = Path(__file__).resolve().parent.parent
POLICY = 'source-id-migration-v1'
DIRECTORY = '.project-intelligence/source-migrations'
GROUPS = ('architecture', 'dependencies', 'changes')
IDENTITY_FIELDS = ('source_id', 'evidence_id', 'source_identity_policy')


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _sha(value):
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def _read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def _rows(root):
    rows = []
    for group in GROUPS:
        path = Path(root) / '.project-intelligence/claims' / (group + '.json')
        current = _read(path, [])
        if not isinstance(current, list):
            raise ValueError('El registro de afirmaciones no es un array: ' + group)
        rows.extend(current)
    return rows


def _catalogue_ids(root):
    data = _read(Path(root) / '.project-intelligence/library/sources.json', {}) or {}
    return {item.get('source_id') for item in data.get('sources', [])
            if isinstance(item, dict) and isinstance(item.get('source_id'), str)}


def _document_identity(root, case_id, evidence):
    ident = evidence.get('document_id')
    if not re.fullmatch(r'[0-9a-f]{64}', str(ident or '')) or evidence.get('document_sha256') != ident:
        raise ValueError('document_identity_missing_or_malformed')
    directory = Path(root) / '.project-intelligence/documents' / ident
    metadata = _read(directory / 'metadata.json')
    original = directory / 'original.pdf'
    if not isinstance(metadata, dict) or not original.is_file():
        raise ValueError('registered_document_missing')
    if hashlib.sha256(original.read_bytes()).hexdigest() != ident:
        raise ValueError('registered_document_hash_mismatch')
    imports = metadata.get('imports', [])
    if not any(item.get('case_id') == case_id for item in imports if isinstance(item, dict)):
        raise ValueError('document_not_registered_to_case')
    # documents.identity_key reads only the pre-existing confirmed identity review.
    return documents.identity_key(root, case_id, evidence)


def _identity(root, claim, evidence):
    kind = evidence.get('type')
    receipt = None
    reviewed = None
    if kind == 'document':
        reviewed = _document_identity(root, claim.get('investigation_id'), evidence)
    elif kind == 'external':
        url = evidence.get('url', '')
        parsed = urlsplit(url)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.username or parsed.password):
            raise ValueError('external_url_invalid')
        linked_id = evidence.get('source_check_id')
        if linked_id:
            receipt = source_check.trusted(evidence, Path(root) / '.project-intelligence/source-checks')
            # Never substitute latest() when the evidence's own receipt is absent or untrusted.
    elif kind == 'file':
        if not isinstance(evidence.get('path'), str) or not evidence['path'].strip():
            raise ValueError('file_reference_missing')
    elif kind == 'commit':
        if not isinstance(evidence.get('ref'), str) or not evidence['ref'].strip():
            raise ValueError('commit_reference_missing')
    else:
        raise ValueError('unsupported_evidence_type')
    identity = source_identity.identify(evidence, receipt, reviewed)
    return identity, ('linked_trusted_source_check' if receipt else
                      'linked_source_check_untrusted_ignored' if kind == 'external' and evidence.get('source_check_id') else
                      'registered_document_review' if reviewed else identity['basis'])


def _inspect_evidence(root, claim, index, evidence, known_ids):
    has_fields = any(key in evidence for key in IDENTITY_FIELDS)
    if source_identity.has_catalog_identity(evidence):
        return None, {'claim_id': claim.get('id'), 'evidence_index': index,
                      'reason': 'already_has_valid_catalog_identity'}
    if has_fields:
        return None, {'claim_id': claim.get('id'), 'evidence_index': index,
                      'reason': 'malformed_or_foreign_identity_fields',
                      'identity_policy': evidence.get('source_identity_policy')}
    try:
        identity, basis = _identity(root, claim, evidence)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return None, {'claim_id': claim.get('id'), 'evidence_index': index,
                      'reason': str(exc)[:160]}
    item_id = hashlib.sha256((str(claim.get('investigation_id', '')) + '\n'
                              + str(claim.get('id', '')) + '\n' + str(index) + '\n'
                              + identity['source_id'] + '\n' + identity['evidence_id']).encode('utf-8')).hexdigest()
    return {
        'item_id': item_id,
        'case_id': claim.get('investigation_id', ''),
        'claim_id': claim.get('id', ''),
        'claim_group': claim.get('category', ''),
        'evidence_index': index,
        'evidence_type': evidence.get('type', ''),
        'legacy_reference': {key: evidence.get(key) for key in ('url', 'title', 'document_id',
                             'document_sha256', 'path', 'ref') if evidence.get(key) not in (None, '')},
        'evidence_sha256': _sha(evidence),
        'proposed_source_id': identity['source_id'],
        'proposed_evidence_id': identity['evidence_id'],
        'identity_policy': source_identity.POLICY,
        'identity_key': identity['identity_key'],
        'identity_signals': identity['signals'],
        'identity_basis': basis,
        'joins_existing_catalogue_source': identity['source_id'] in known_ids,
        'status': 'eligible',
    }, None


def build_plan(root=ROOT, rows=None):
    """Build a dry-run manifest in memory; no claims or evidence are changed."""
    root = Path(root).resolve()
    rows = _rows(root) if rows is None else rows
    known_ids = _catalogue_ids(root)
    items, skipped = [], []
    for claim in rows:
        for index, evidence in enumerate(claim.get('evidence', [])):
            if not isinstance(evidence, dict):
                skipped.append({'claim_id': claim.get('id'), 'evidence_index': index,
                                'reason': 'evidence_record_not_an_object'})
                continue
            candidate, reason = _inspect_evidence(root, claim, index, evidence, known_ids)
            if candidate:
                items.append(candidate)
            elif reason:
                skipped.append(reason)
    items.sort(key=lambda item: (item['case_id'], item['claim_id'], item['evidence_index']))
    skipped.sort(key=lambda item: (str(item.get('claim_id', '')), item.get('evidence_index', -1), item['reason']))
    identity = {'policy': POLICY, 'items': items, 'skipped': skipped}
    ident = hashlib.sha256(_json_bytes(identity)).hexdigest()
    return {
        **identity,
        'id': ident,
        'status': 'preview',
        'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'summary': {'eligible': len(items), 'skipped': len(skipped),
                    'existing_source_joins': sum(item['joins_existing_catalogue_source'] for item in items)},
        'safety': {
            'default_is_dry_run': True,
            'claim_text_changed': False,
            'evidence_content_changed': False,
            'semantic_roles_changed': False,
            'reviews_or_verdicts_changed': False,
            'source_check_receipts_changed': False,
        },
    }


def write_plan(root=ROOT, rows=None):
    plan = build_plan(root, rows)
    directory = Path(root) / DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (plan['id'] + '.json')
    existing = _read(path)
    if existing and existing.get('status') in ('applied', 'applying'):
        # A completed plan is immutable. New evidence state produces a new ID.
        raise ValueError('El manifiesto de esta migración ya se aplicó')
    plan['integrity_sha256'] = _manifest_digest(plan)
    _atomic_json(path, plan)
    return plan, path


def _manifest_digest(manifest):
    return _sha({key: value for key, value in manifest.items() if key != 'integrity_sha256'})


def apply_manifest(root, manifest_path, persist_callback=None, refresh_callback=None):
    """Apply a preview idempotently and reconcile interrupted finalization safely."""
    root = Path(root).resolve()
    path = Path(manifest_path).resolve()
    directory = (root / DIRECTORY).resolve()
    if directory not in path.parents:
        raise ValueError('El manifiesto debe estar dentro del directorio de migraciones del proyecto')
    manifest = _read(path)
    if (not isinstance(manifest, dict) or manifest.get('policy') != POLICY
            or manifest.get('id') != path.stem
            or manifest.get('integrity_sha256') != _manifest_digest(manifest)):
        raise ValueError('Manifiesto de migración inválido o modificado')
    if not manifest.get('items'):
        raise ValueError('La vista previa no contiene registros migrables')

    status = manifest.get('status')
    if status == 'applied':
        return manifest
    if status not in ('preview', 'applying', 'apply_error'):
        raise ValueError('Estado de manifiesto no aplicable: ' + str(status))

    rows = _rows(root)
    indexed = {(claim.get('id'), claim.get('investigation_id')): claim for claim in rows}
    staged = copy.deepcopy(rows)
    staged_indexed = {(claim.get('id'), claim.get('investigation_id')): claim for claim in staged}

    def current_state(item):
        original = indexed.get((item.get('claim_id'), item.get('case_id')))
        index = item.get('evidence_index')
        if (original is None or type(index) is not int
                or not 0 <= index < len(original.get('evidence', []))):
            return 'conflict'
        evidence = original['evidence'][index]
        if (evidence.get('source_id') == item.get('proposed_source_id')
                and evidence.get('evidence_id') == item.get('proposed_evidence_id')
                and evidence.get('source_identity_policy') == source_identity.POLICY):
            provenance = evidence.get('source_migration')
            if (isinstance(provenance, dict) and provenance.get('policy') == POLICY
                    and provenance.get('manifest_id') == manifest['id']
                    and provenance.get('item_id') == item.get('item_id')):
                return 'migrated'
            return 'conflict'
        if (any(field in evidence for field in IDENTITY_FIELDS)
                or _sha(evidence) != item.get('evidence_sha256')):
            return 'conflict'
        return 'unmigrated'

    states = [current_state(item) for item in manifest['items']]
    if 'conflict' in states or ('migrated' in states and 'unmigrated' in states):
        raise ValueError('Estado parcial o distinto al manifiesto; se requiere reconciliación manual')

    def callbacks():
        nonlocal persist_callback, refresh_callback
        if persist_callback is None or refresh_callback is None:
            import pipeline
            if Path(pipeline.ROOT).resolve() != root:
                raise ValueError('La migración sólo puede usar la ruta activa del proyecto')
            persist_callback = persist_callback or pipeline.persist
            refresh_callback = refresh_callback or library.refresh

    if states and all(state == 'migrated' for state in states):
        callbacks()
        try:
            refresh_callback(rows)
        except Exception as exc:
            manifest['status'] = 'apply_error'
            manifest['error'] = ('refresh reconciliation: ' + type(exc).__name__ + ': ' + str(exc))[:1000]
            manifest['integrity_sha256'] = _manifest_digest(manifest)
            _atomic_json(path, manifest)
            raise
        manifest['status'] = 'applied'
        manifest['error'] = ''
        manifest['applied_at'] = manifest.get('applied_at') or dt.datetime.now(dt.timezone.utc).isoformat()
        for item in manifest['items']:
            item['status'] = 'applied'
        manifest['integrity_sha256'] = _manifest_digest(manifest)
        _atomic_json(path, manifest)
        return manifest

    for item in manifest['items']:
        key = (item.get('claim_id'), item.get('case_id'))
        original = indexed.get(key)
        target = staged_indexed.get(key)
        index = item.get('evidence_index')
        if (original is None or target is None or type(index) is not int
                or not 0 <= index < len(original.get('evidence', []))):
            raise ValueError('Un registro de la vista previa ya no existe; vuelve a generar el plan')
        evidence = original['evidence'][index]
        if (_sha(evidence) != item.get('evidence_sha256')
                or source_identity.has_catalog_identity(evidence)
                or any(field in evidence for field in IDENTITY_FIELDS)):
            raise ValueError('La evidencia cambió después de la vista previa; no se aplicó nada')
        candidate, _ = _inspect_evidence(root, original, index, evidence, _catalogue_ids(root))
        if not candidate or any(candidate.get(name) != item.get(name) for name in
                                ('item_id', 'proposed_source_id', 'proposed_evidence_id', 'identity_key')):
            raise ValueError('La identidad propuesta cambió; no se aplicó nada')
        target_evidence = target['evidence'][index]
        target_evidence.update(source_id=item['proposed_source_id'],
                               evidence_id=item['proposed_evidence_id'],
                               source_identity_policy=source_identity.POLICY,
                               source_migration={
                                   'policy': POLICY,
                                   'manifest_id': manifest['id'],
                                   'item_id': item['item_id'],
                                   'identity_basis': item['identity_basis'],
                                   'migrated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                               })
    manifest['status'] = 'applying'
    manifest.pop('error', None)
    manifest['integrity_sha256'] = _manifest_digest(manifest)
    _atomic_json(path, manifest)
    try:
        callbacks()
        persist_callback(staged)
        refresh_callback(staged)
    except Exception as exc:
        manifest['status'] = 'apply_error'
        manifest['error'] = (type(exc).__name__ + ': ' + str(exc))[:1000]
        manifest['integrity_sha256'] = _manifest_digest(manifest)
        _atomic_json(path, manifest)
        raise
    manifest['status'] = 'applied'
    manifest['applied_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
    for item in manifest['items']:
        item['status'] = 'applied'
    manifest['integrity_sha256'] = _manifest_digest(manifest)
    _atomic_json(path, manifest)
    return manifest


def _main(argv=None):
    parser = argparse.ArgumentParser(description='Vista previa y migración explícita de IDs de fuentes históricos')
    parser.add_argument('--root', type=Path, default=ROOT, help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('plan', help='Crear manifiesto de vista previa; no modifica evidencia')
    apply = subparsers.add_parser('apply', help='Aplicar una vista previa intacta y volver a validar sus entradas')
    apply.add_argument('--manifest', required=True, help='Ruta del manifiesto emitido por plan')
    args = parser.parse_args(argv)
    if args.command in (None, 'plan'):
        plan, path = write_plan(args.root)
        print(json.dumps({'id': plan['id'], 'status': plan['status'], 'summary': plan['summary'],
                          'path': str(path)}, ensure_ascii=False))
        return 0
    manifest = apply_manifest(args.root, args.manifest)
    print(json.dumps({'id': manifest['id'], 'status': manifest['status'],
                      'applied': manifest['summary']['eligible']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(_main())
