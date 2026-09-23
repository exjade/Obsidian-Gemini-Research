"""Conservative publication gate over the explicitly admitted scope."""
import hashlib
import json
import research_scope

POLICY = 'closure-v1'


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
        if bounded.get('status')=='excluded_with_limit':
            item.update(resolved=True,resolution='limited',
                        reason=bounded.get('reason') or 'El protocolo limitado no resolvió esta parte de la pregunta.',
                        action='Consultar los intentos realizados y la evidencia que sigue faltando.')
            result['limited']+=1
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
        if item['resolution']=='limited':
            label='Parte de la pregunta que no pudimos responder'
        else:
            label = 'Con respaldo registrado' if item['resolution']=='supported' else 'Refutación explícita registrada'
        text += '- **' + label + ':** ' + item['claim'] + ' (ficha: `' + item['id'] + '`).\n'
    if assessment.get('limited'):
        text += '\n## Parte de la pregunta que no pudimos responder\n\n'
        for item in assessment['items']:
            if item.get('resolution')=='limited':
                text += '- '+item['claim']+': '+item['reason']+'\n'
    return text + '\nEstos controles no garantizan verdad absoluta; consulta las fuentes, la revisión crítica y sus límites.\n'
