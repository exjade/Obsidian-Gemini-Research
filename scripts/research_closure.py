"""Conservative publication gate over the explicitly admitted scope."""
import hashlib
import json
import uuid
import research_scope

POLICY = 'closure-v1'
SCIENTIFIC_RESOLUTION_POLICY = 'scientific-resolution-v1'


def scientific_resolution(formulation, matrices, audit, skeptic, receipts, evidence_mode='question_search',
                          documents_considered=False, affected_conclusions=None):
    """Build an explainable resolution from persisted, passage-level audit rows.

    This projection is deliberately separate from the historical claim verdict.
    It never treats a failed/missing search as evidence against a claim.
    """
    from research_agents import DIMENSIONS, stable_digest
    claim = formulation.get('claim', '')
    plan = formulation.get('plan', {})
    rows_by_id={(row.get('source_id'),row.get('evidence_id')):row
                for matrix in matrices for row in matrix.get('matrix', [])}
    rows = list(rows_by_id.values())
    dimensions = {}
    for dimension in DIMENSIONS:
        evidence = []
        for row in rows:
            relation = row.get('dimensions', {}).get(dimension, 'unreported')
            evidence.append({'source_id': row.get('source_id'), 'evidence_id': row.get('evidence_id'),
                             'relation': relation, 'basis': row.get('basis', ''),
                             'source_status': row.get('source_status') or row.get('primary_status')})
        direct_contradiction = any(item['relation'] == 'contradicts' and
                                   next((row.get('source_status') for row in rows
                                         if row.get('source_id')==item['source_id'] and row.get('evidence_id')==item['evidence_id']),None)=='confirmed_primary'
                                   for item in evidence)
        direct_support = any(item['relation'] == 'supports' and
                             next((row.get('source_status') for row in rows
                                   if row.get('source_id')==item['source_id'] and row.get('evidence_id')==item['evidence_id']),None)=='confirmed_primary'
                             for item in evidence)
        rows_for_dimension=[row for row in rows if row.get('dimensions',{}).get(dimension) in ('supports','contradicts')]
        statuses={row.get('source_status') or row.get('primary_status') for row in rows_for_dimension}
        mixed=direct_contradiction and direct_support
        strength = ('mixed' if mixed else
                    'contradictory' if direct_contradiction else
                    'unreported' if not rows_for_dimension else
                    'indirect' if statuses and statuses <= {'secondary','uncertain','declared_primary'} else
                    'direct' if statuses <= {'confirmed_primary'} else 'partial')
        dimensions[dimension] = {
            'formulation': plan.get('matrix', {}).get(dimension, ''),
            'state': ('unresolved' if mixed else 'contradicted' if direct_contradiction else
                      'supported' if direct_support else 'unresolved'),
            'evidence_strength': strength,
            'evidence': evidence,
            'retrieval_targets': [target for target in plan.get('retrieval_targets', [])
                                  if dimension in target.get('dimension_ids', [])],
        }
    required = [key for key in DIMENSIONS if str(dimensions[key]['formulation']).strip()]
    unresolved = [key for key in required if dimensions[key]['state'] == 'unresolved']
    contradiction = any(dimensions[key]['state'] == 'contradicted' for key in required)
    support = bool(required) and all(dimensions[key]['state'] == 'supported' for key in required)
    decision = audit.get('decision') if isinstance(audit, dict) else None
    criteria=set(audit.get('indeterminacy_criteria',[])) if isinstance(audit,dict) else set()
    contradiction_targets={dimension for target in plan.get('retrieval_targets',[])
                           if target.get('purpose')=='contradiction' for dimension in target.get('dimension_ids',[])}
    contradiction_searched={dimension for row in receipts if 'contradiction' in row.get('target_purposes',[])
                            for dimension in row.get('target_dimensions',[])}
    if (decision == 'sufficient_support' and skeptic.get('verdict') == 'VERIFIED' and support
            and not audit.get('unresolved_dimensions',[])
            and contradiction_targets.issubset(contradiction_searched)):
        resolution = 'supported'
    elif decision == 'direct_contradiction' and skeptic.get('verdict') == 'CONTRADICTED' and contradiction:
        resolution = 'refuted'
    else:
        rounds_recorded = {row.get('round') for row in receipts}
        search_complete = (rounds_recorded >= {1,2,3} or any(
            any(int(row.get('remaining',{}).get(key,1))==0 for key in
                ('global_queries','global_pages','seconds')) for row in receipts))
        attempted={dimension for row in receipts for dimension in row.get('target_dimensions',[])}
        targets_attempted = bool(unresolved) and set(unresolved).issubset(attempted)
        contradicted_searched={dimension for row in receipts if 'contradiction' in row.get('target_purposes',[])
                               for dimension in row.get('target_dimensions',[])}
        contradiction_targets_attempted=set(unresolved).issubset(contradicted_searched)
        explicit_criteria={'bounded_search_complete','unresolved_dimensions_targeted','all_supplied_inputs_considered'}
        auditor_matches=set(audit.get('unresolved_dimensions',[]))==set(unresolved) if isinstance(audit,dict) else False
        if (not support and not contradiction and unresolved and search_complete and targets_attempted
                and contradiction_targets_attempted and documents_considered and decision in ('exhausted', 'continue')
                and explicit_criteria.issubset(criteria) and auditor_matches):
            resolution = 'indeterminate'
        else:
            resolution = 'unresolved'
    return {
        'policy': SCIENTIFIC_RESOLUTION_POLICY,
        'version': 1,
        'resolution_id': uuid.uuid4().hex,
        'resolution': resolution,
        'claim_id': formulation.get('claim_id'),
        'claim_sha256': stable_digest(claim),
        'input_fingerprint': formulation.get('input_fingerprint'),
        'evidence_mode': evidence_mode,
        'audit_decision': decision,
        'skeptic_verdict': skeptic.get('verdict') if isinstance(skeptic, dict) else None,
        'documents_considered': bool(documents_considered),
        'indeterminacy_criteria': sorted(criteria) if resolution == 'indeterminate' else [],
        'audit_unresolved_dimensions': sorted(audit.get('unresolved_dimensions', []))
            if isinstance(audit, dict) else [],
        'dimensions': dimensions,
        'unresolved_dimensions': unresolved,
        'affected_conclusions': list(affected_conclusions or []),
        'budget_receipts': list(receipts),
        'competing_hypotheses': list(plan.get('competing_hypotheses',[])),
        'falsification_criteria': list(plan.get('falsification_criteria',[])),
        'subquestions': list(formulation.get('subquestions',[])),
        'auditor_explanation': (audit or {}).get('explanation', ''),
        'limitations': ('El protocolo acotado no resolvió estas dimensiones; esto no demuestra que no existan estudios.'
                        if resolution == 'indeterminate' else ''),
        'created_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    }


def validate_scientific_resolution(claim, record):
    """Revalidate a stored v1 scientific outcome before it can close scope.

    This checks the persisted, deterministic projection, not provider prose alone.
    It never changes the legacy claim verdict.
    """
    from research_agents import DIMENSIONS, stable_digest
    if not isinstance(record, dict):
        raise ValueError('El registro de resolución científica no es válido; requiere reevaluación.')
    if record.get('policy') != SCIENTIFIC_RESOLUTION_POLICY or record.get('version') != 1:
        raise ValueError('La resolución científica usa una política o versión distinta; requiere reevaluación.')
    if not isinstance(record.get('resolution_id'), str) or not record['resolution_id'].strip():
        raise ValueError('Falta el identificador de la resolución científica; requiere reevaluación.')
    if not isinstance(record.get('input_fingerprint'), str) or not record['input_fingerprint'].strip():
        raise ValueError('Falta la huella de entradas de la resolución científica; requiere reevaluación.')
    if record.get('claim_id') != claim.get('id') or record.get('claim_sha256') != stable_digest(claim.get('claim', '')):
        raise ValueError('La resolución científica corresponde a otra versión de la afirmación; requiere reevaluación.')
    if record.get('resolution') not in {'supported', 'refuted', 'indeterminate', 'unresolved'}:
        raise ValueError('La resolución científica contiene un resultado desconocido; requiere reevaluación.')
    if record.get('evidence_mode') not in {'question_search', 'documents_only', 'documents_plus_search'}:
        raise ValueError('Falta un modo de evidencia reconocido; requiere reevaluación.')
    dimensions = record.get('dimensions')
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        raise ValueError('La matriz de dimensiones está incompleta o usa otro esquema; requiere reevaluación.')
    required = {key for key, value in dimensions.items()
                if isinstance(value, dict) and isinstance(value.get('formulation'), str)
                and value['formulation'].strip()}
    if not required:
        raise ValueError('La resolución no identifica dimensiones requeridas; requiere reevaluación.')
    allowed_states = {'supported', 'contradicted', 'unresolved'}
    for key, dimension in dimensions.items():
        if (not isinstance(dimension, dict) or dimension.get('state') not in allowed_states
                or dimension.get('evidence_strength') not in
                {'direct', 'partial', 'indirect', 'contradictory', 'mixed', 'unreported'}
                or not isinstance(dimension.get('evidence'), list)):
            raise ValueError('La dimensión ' + key + ' no tiene una estructura válida; requiere reevaluación.')
        for passage in dimension['evidence']:
            if (not isinstance(passage, dict) or passage.get('relation') not in
                    {'supports', 'contradicts', 'mismatch', 'unreported'}
                    or not isinstance(passage.get('source_id'), str) or not passage['source_id'].strip()
                    or not isinstance(passage.get('evidence_id'), str) or not passage['evidence_id'].strip()):
                raise ValueError('La matriz contiene una relación sin pasaje identificable; requiere reevaluación.')
    unresolved = {key for key in required if dimensions[key]['state'] == 'unresolved'}
    if set(record.get('unresolved_dimensions', [])) != unresolved:
        raise ValueError('La lista de dimensiones pendientes no coincide con la matriz; requiere reevaluación.')
    receipts = record.get('budget_receipts')
    if (not isinstance(receipts, list) or any(not isinstance(receipt, dict)
            or not isinstance(receipt.get('target_dimensions', []), list)
            or not isinstance(receipt.get('target_purposes', []), list) for receipt in receipts)):
        raise ValueError('Faltan recibos del presupuesto de búsqueda; requiere reevaluación.')
    if (not isinstance(record.get('unresolved_dimensions'), list)
            or not isinstance(record.get('audit_unresolved_dimensions'), list)):
        raise ValueError('La auditoría no conserva listas válidas de dimensiones pendientes.')
    result = record['resolution']
    if result == 'supported':
        if (unresolved or record.get('audit_decision') != 'sufficient_support'
                or record.get('skeptic_verdict') != 'VERIFIED'):
            raise ValueError('La resolución de respaldo no conserva las revisiones requeridas.')
        for key in required:
            dimension = dimensions[key]
            direct = any(p.get('relation') == 'supports' and p.get('source_status') == 'confirmed_primary'
                         for p in dimension['evidence'])
            if dimension['state'] != 'supported' or dimension['evidence_strength'] != 'direct' or not direct:
                raise ValueError('La dimensión ' + key + ' carece de respaldo primario directo.')
            if any(p.get('relation') == 'contradicts' for p in dimension['evidence']):
                raise ValueError('La dimensión ' + key + ' también conserva evidencia contradictoria.')
            if not any(key in receipt.get('target_dimensions', []) and
                       'contradiction' in receipt.get('target_purposes', []) for receipt in receipts):
                raise ValueError('Falta la búsqueda contradictoria registrada para ' + key + '.')
    elif result == 'refuted':
        direct = any(dimensions[key]['state'] == 'contradicted' and
                     dimensions[key]['evidence_strength'] == 'contradictory' and
                     any(p.get('relation') == 'contradicts' and
                         p.get('source_status') == 'confirmed_primary'
                         for p in dimensions[key]['evidence']) for key in required)
        if not direct or record.get('audit_decision') != 'direct_contradiction' or record.get('skeptic_verdict') != 'CONTRADICTED':
            raise ValueError('La refutación no conserva un pasaje primario directo y ambas revisiones.')
    elif result == 'indeterminate':
        criteria = {'bounded_search_complete', 'unresolved_dimensions_targeted',
                    'all_supplied_inputs_considered'}
        rounds = {receipt.get('round') for receipt in receipts}
        complete = rounds >= {1, 2, 3} or any(
            isinstance(receipt.get('remaining'), dict) and any(
                receipt['remaining'].get(key) == 0 for key in ('global_queries', 'global_pages', 'seconds'))
            for receipt in receipts)
        if (not unresolved or not complete or not record.get('documents_considered')
                or not criteria.issubset(set(record.get('indeterminacy_criteria', [])))
                or set(record.get('audit_unresolved_dimensions', [])) != unresolved
                or record.get('audit_decision') not in {'exhausted', 'continue'}
                or record.get('skeptic_verdict') in {'VERIFIED', 'CONTRADICTED'}
                or any(dimensions[key]['state'] == 'contradicted' for key in required)
                or any(dimensions[key]['state'] in {'supported', 'contradicted'} for key in unresolved)
                or not isinstance(record.get('limitations'), str)
                or 'no demuestra que no existan estudios' not in record['limitations']):
            raise ValueError('La indeterminación no conserva los criterios y límites exigidos; requiere reevaluación.')
        for key in unresolved:
            if not any(key in receipt.get('target_dimensions', []) for receipt in receipts):
                raise ValueError('Falta un intento de búsqueda para la dimensión ' + key + '.')
            if not any(key in receipt.get('target_dimensions', []) and
                       'contradiction' in receipt.get('target_purposes', []) for receipt in receipts):
                raise ValueError('Falta búsqueda contradictoria para la dimensión ' + key + '.')
    return result


def guidance(item):
    user=item.get('owner')=='usuario'
    item['why_it_matters']=('Define qué responderá la investigación sin perder el trabajo anterior.' if user else
        'Sin resolver este punto, la conclusión podría decir más de lo que demuestra la evidencia.')
    item['system_attempts']=(['Conservar hipótesis, evaluaciones y documentos anteriores mientras decides el alcance.'] if user else [
        'Al reevaluar: consultar fragmentos de los PDFs asociados a este expediente.',
        'Localizar hasta seis pasajes candidatos de otros expedientes y revisar su pertinencia con Collector y Skeptic.',
        'Reutilizar recopilación completa vigente si corresponde y comprobar otra vez las páginas seleccionadas.',
        'Si falta acceso: conservar el bloqueo. Recuperación alternativa automática todavía no disponible.'])
    item['attempt_state']='available_on_reevaluation' if not user else 'awaiting_scope_decision'
    item['help_needed']=('Tu decisión sobre qué hipótesis incluir o descartar.' if user else
        'No necesitas auditar las fuentes ahora. Si la reevaluación sigue bloqueada, puedes aportar una copia accesible; no cambia por sí sola el veredicto.')
    return item


def assess(meta, rows, validate):
    result = {'policy': POLICY, 'ready': False, 'resolved': 0, 'total': 0, 'limited': 0,
              'items': [], 'blockers': []}
    try:
        selected = research_scope.admitted(meta, rows)
    except (ValueError, KeyError) as exc:
        result['blockers'].append(guidance({'reason': str(exc), 'owner': 'usuario',
                                   'action': 'Revisar y aprobar el alcance en Pregunta y alcance.'}))
        return result
    result['total'] = len(selected)
    result['input_sha256'] = hashlib.sha256(json.dumps(
        {'scope': meta['scope'], 'claims': [{k:v for k,v in c.items() if k!='writing_history'} for c in selected]}, sort_keys=True,
        ensure_ascii=False).encode()).hexdigest()
    for claim in selected:
        item = guidance({'id': claim['id'], 'claim': claim['claim'], 'resolved': False,
                'owner': 'sistema', 'action': 'Solicitar reevaluación con los materiales disponibles desde la ficha.'})
        status = claim.get('status')
        bounded=claim.get('bounded_resolution') or {}
        history=claim.get('scientific_resolution_history') or []
        latest=(history[-1] if isinstance(history,list) and history else
                None if 'scientific_resolution_history' in claim and not isinstance(history,list) else
                claim.get('scientific_resolution'))
        has_scientific=('scientific_resolution_history' in claim or 'scientific_resolution' in claim)
        if has_scientific:
            try:
                resolution=validate_scientific_resolution(claim,latest)
                if resolution in {'supported','refuted','indeterminate'}:
                    item.update(resolved=True,resolution=resolution,
                                reason=(latest.get('limitations') if resolution=='indeterminate' else
                                        'Resolución científica vigente; el veredicto histórico no se modificó.'),
                                action='Puedes añadir evidencia y reevaluar; esta resolución y su historial se conservarán.')
                    if resolution=='indeterminate':result['limited']+=1
                else:
                    item.update(resolved=False,resolution='unresolved',
                                reason='La evaluación científica más reciente no llegó a una resolución.',
                                action='El sistema debe continuar la recuperación o registrar los límites que faltan.')
            except (ValueError, KeyError, TypeError) as exc:
                item.update(resolved=False,resolution='unresolved',
                            reason='La resolución científica registrada está desactualizada o incompleta: '+str(exc),
                            action='Solicita reevaluación; no se usará este registro para cerrar la hipótesis.')
        elif bounded.get('status')=='excluded_with_limit':
            item.update(resolved=False,resolution='unresolved',
                        reason=bounded.get('reason') or 'El protocolo limitado terminó, pero no cumple los criterios de una resolución científica.',
                        action='El sistema necesita más evidencia o una indeterminación justificada; no se concluye que no existan estudios.')
        elif status not in ('VERIFIED', 'CONTRADICTED'):
            item['reason'] = {
                'UNVERIFIED': 'Todavía no tiene revisión crítica.',
                'PARTIAL': 'El respaldo sólo permite una conclusión parcial.',
                'UNSUPPORTED': 'Falta respaldo suficiente; esto no refuta la hipótesis.'
            }.get(status, 'El veredicto no permite resolver esta hipótesis.')
        else:
            try:
                validate(claim)
                item.update(resolved=True, resolution='supported' if status == 'VERIFIED' else 'refuted',
                            reason='Revisión y comprobaciones vigentes registradas.', action='Consultar respaldo y límites del veredicto.')
            except (ValueError, KeyError, OSError) as exc:
                item['reason'] = 'La comprobación necesita atención: ' + str(exc)
        result['items'].append(item)
        if item['resolved']:
            result['resolved'] += 1
        else:
            result['blockers'].append(item)
    if meta.get('scope_proposal'):
        result['blockers'].append(guidance({'reason':'Hay una ampliación propuesta pendiente de decisión; el alcance anterior se conserva.',
                                   'owner':'usuario','action':'Aprobar las hipótesis adicionales o descartar la propuesta en Pregunta y alcance.'}))
    result['ready'] = bool(selected) and not result['blockers']
    return result


def provisional(title, assessment):
    text = '# ' + title + '\n\n> [!warning] Informe provisional — investigación inconclusa\n'
    text += '> La ejecución terminó, pero no se consolidaron conclusiones. No confundir falta de respaldo con refutación.\n\n'
    text += f"Hipótesis resueltas del alcance aprobado: {assessment['resolved']}/{assessment['total']}.\n\n"
    for blocker in assessment['blockers']:
        if not blocker.get('id'):
            text += blocker['reason']+'\n\nSiguiente acción: '+blocker['action']+'\n\n'
    for item in assessment['items']:
        text += '## ' + item['claim'] + '\n\n'
        text += ('Revisión disponible; no consolidada mientras existan pendientes.' if item['resolved'] else 'Pendiente de resolución.') + '\n\n'
        text += item['reason'] + '\n\nResponsable: ' + item['owner'] + '.\n\nSiguiente acción: ' + item['action'] + '\n\n'
        text += 'Por qué importa: '+item['why_it_matters']+'\n\n'
        text += 'Plan disponible al reevaluar (no implica que ya se haya ejecutado):\n'+''.join('- '+step+'\n' for step in item['system_attempts'])+'\n'
        text += item['help_needed']+'\n\n'
    text += 'Las fichas conservan fuentes, pasajes, veredictos e historial. Una indeterminación justificada necesita criterios y revisión explícitos; el sistema no la deduce de un enlace bloqueado.\n'
    return text


def scope_summary(assessment):
    text = '\n## Resolución del alcance aprobado\n\n'
    for item in assessment['items']:
        if item['resolution']=='indeterminate':
            label='Parte de la pregunta que no pudimos responder'
        elif item['resolution']=='supported':
            label='Con respaldo registrado'
        elif item['resolution']=='refuted':
            label='Refutación explícita registrada'
        else:
            label='Pendiente: el protocolo todavía no permite resolverla'
        text += '- **' + label + ':** ' + item['claim'] + ' (ficha: `' + item['id'] + '`).\n'
        if item.get('reason'):
            text+='  Motivo: '+item['reason']+'\n'
    if assessment.get('limited'):
        text += '\n## Parte de la pregunta que no pudimos responder\n\n'
        for item in assessment['items']:
            if item.get('resolution')=='limited':
                text += '- '+item['claim']+': '+item['reason']+'\n'
    return text + '\nEstos controles no garantizan verdad absoluta; consulta las fuentes, la revisión crítica y sus límites.\n'
