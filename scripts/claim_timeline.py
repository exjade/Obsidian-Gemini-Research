"""Read-only, deterministic per-claim projection of durable research records."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any, Iterable, Mapping


def _event_id(category: str, claim_id: str, source_id: str, subtype: str = "") -> str:
    raw = "|".join((category, claim_id, source_id, subtype))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _time_key(value: Any) -> tuple[int, float, str]:
    if not isinstance(value, str) or not value.strip():
        return (1, 0.0, "")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return (1, 0.0, "")
        return (0, parsed.astimezone(dt.timezone.utc).timestamp(), "")
    except (ValueError, OverflowError):
        return (1, 0.0, value)


def _operation_time(value: Any) -> dt.datetime | None:
    """Parse only an explicit timezone-aware timestamp; legacy fallbacks stay unknown."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(dt.timezone.utc)


def _first_operation_time(row: Mapping[str, Any], *fields: str) -> dt.datetime | None:
    """Return the first valid explicit time for ordering; never writes fallbacks."""
    for field in fields:
        parsed = _operation_time(row.get(field))
        if parsed is not None:
            return parsed
    return None


def _project_research_operation(row: Mapping[str, Any], *, is_current_result: bool) -> dict[str, Any]:
    """Normalize persisted operation data into a complete, read-only history DTO.

    Missing legacy fields remain unknown (``None``); defaults below describe
    empty collections only where the field's contract is inherently a list.
    The original record and nested values are never rewritten.
    """
    projected = dict(row)
    input_data = row.get("input_data") if isinstance(row.get("input_data"), Mapping) else {}
    result = row.get("result")
    result_data = result if isinstance(result, Mapping) else {}

    operation_id = row.get("operation_id") or row.get("id")
    projected.update({
        "operation_id": operation_id,
        "id": row.get("id") or operation_id,
        "requested_at": row.get("requested_at"),
        "created_at": row.get("created_at"),
        "started_at": row.get("started_at"),
        "updated_at": row.get("updated_at"),
        "finished_at": row.get("finished_at"),
        "evidence_mode": row.get("evidence_mode") or input_data.get("evidence_mode"),
        "document_ids": row.get("document_ids", input_data.get("document_ids", [])),
        "claim_version": row.get("claim_version", input_data.get("claim_version")),
        "input_fingerprint": row.get("input_fingerprint", input_data.get("input_fingerprint")),
        "input_data": row.get("input_data"),
        "status": row.get("status"),
        "stage": row.get("stage"),
        "progress": row.get("progress"),
        "budget_plan": row.get("budget_plan"),
        "budget_receipts": result_data.get("budget_receipts", []),
        "result": result,
        "error": row.get("error"),
        "frontend_status": row.get("frontend_status"),
        "frontend_error": row.get("frontend_error"),
        "engine_status": row.get("engine_status"),
        "engine_error": row.get("engine_error"),
        "attempt_history": row.get("attempt_history", []),
        "is_current_result": is_current_result,
    })
    return projected


def project_claim_research_history(operations: Iterable[Mapping[str, Any]], claim_id: str) -> dict[str, Any]:
    """Return a deterministic, read-only projection of a claim's research operations.

    The operation records remain intact. requested_at is preferred for ordering;
    created_at is an ordering fallback only, never copied into another field.
    Missing/naive timestamps are not inferred from update times or filesystem
    metadata and sort after dated records.
    """
    selected = [dict(row) for row in operations
                if isinstance(row, Mapping) and row.get("kind") == "claim_research"
                and row.get("claim_id") == claim_id]

    def order_key(row: Mapping[str, Any]) -> tuple[int, float, str]:
        timestamp = _first_operation_time(row, "requested_at", "created_at")
        # Newest first; operation ID is the stable tie-breaker, including legacy rows.
        return (0, -timestamp.timestamp(), str(row.get("operation_id") or row.get("id") or "")) if timestamp else (
            1, 0.0, str(row.get("operation_id") or row.get("id") or ""))

    selected.sort(key=order_key)
    latest = selected[0] if selected else None
    completed_statuses = {"done", "resolved", "completed_with_limits"}

    def completion_key(row: Mapping[str, Any]) -> tuple[int, float, str]:
        timestamp = _first_operation_time(row, "finished_at", "requested_at", "created_at")
        return (0, -timestamp.timestamp(), str(row.get("operation_id") or row.get("id") or "")) if timestamp else (
            1, 0.0, str(row.get("operation_id") or row.get("id") or ""))

    completed = [row for row in selected
                 if row.get("status") in completed_statuses and row.get("result") is not None]
    current_completed_source = min(completed, key=completion_key) if completed else None
    current_id = (current_completed_source.get("operation_id") or current_completed_source.get("id")) \
        if current_completed_source else None
    projected = [_project_research_operation(
        row,
        is_current_result=bool(current_id and (row.get("operation_id") or row.get("id")) == current_id),
    ) for row in selected]
    by_id = {str(row.get("operation_id") or row.get("id") or ""): row for row in projected}
    latest_id = (latest.get("operation_id") or latest.get("id")) if latest else None
    current_completed = by_id.get(str(current_id)) if current_id else None
    latest_operation = by_id.get(str(latest_id)) if latest_id else None
    return {
        "operations": projected,
        "latest_operation": latest_operation,
        "current_completed": current_completed,
        "has_active": any(row.get("status") in {"queued", "running"} for row in selected),
    }


def _build_claim_timeline_legacy_dto(claim: Mapping[str, Any], *, operations: Iterable[Mapping[str, Any]] = (),
                         human_reviews: Iterable[Mapping[str, Any]] = (),
                         reformulations: Iterable[Mapping[str, Any]] = (),
                         scope_history: Iterable[Mapping[str, Any]] = (),
                         legacy_source_checks: Iterable[Mapping[str, Any]] = (),
                         revisions: Iterable[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    """Project records without writing, inferring missing dates, or merging semantics."""
    claim_id = str(claim.get("id") or "")
    if not claim_id:
        return []
    events: list[dict[str, Any]] = []

    def add(category: str, event: str, time: Any, source_type: str, source_id: Any,
            title: str, summary: str, *, operation_id: Any = None, legacy: bool = False,
            ref: str | None = None, details: Mapping[str, Any] | None = None) -> None:
        stable_source = str(source_id or "")
        if not stable_source:
            return
        events.append({
            "event_id": _event_id(category, claim_id, stable_source, event),
            "category": category, "event": event, "case_id": claim.get("investigation_id"),
            "claim_id": claim_id, "occurred_at": time if isinstance(time, str) and time else None,
            "source_record_type": source_type, "source_record_id": stable_source,
            "operation_id": str(operation_id) if operation_id else None,
            "title": title, "summary": summary, "legacy": bool(legacy), "ref": ref,
            "details": dict(details or {}),
        })

    add("claim", "created", claim.get("created_at"), "claim", claim_id,
        "Hipótesis creada", str(claim.get("claim", "")), legacy=not bool(claim.get("created_at")), ref="claims")

    for evidence in claim.get("evidence") or []:
        if not isinstance(evidence, Mapping) or evidence.get("type") != "document":
            continue
        document_id = evidence.get("document_id") or evidence.get("source_id")
        if not document_id:
            continue
        add("document", "associated", evidence.get("associated_at") or evidence.get("imported_at"),
            "claim.evidence.document", evidence.get("evidence_id") or document_id,
            "Documento asociado a la hipótesis", str(evidence.get("name") or evidence.get("filename") or document_id),
            legacy=not bool(evidence.get("associated_at") or evidence.get("imported_at")), ref="sources",
            details={"document_id": document_id, "evidence_id": evidence.get("evidence_id"),
                     "identity": evidence.get("identity"), "location": evidence.get("location")})

    # Only actual status transitions are verdict events.
    for index, row in enumerate(claim.get("provenance") or []):
        if not isinstance(row, Mapping) or row.get("previous_status") == row.get("status"):
            continue
        record_id = row.get("revision_id") or row.get("run_id") or row.get("id")
        if not record_id:
            record_id = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        add("verdict_change", "changed", row.get("reviewed_at"), "claim.provenance", record_id,
            "Cambió el veredicto", f"{row.get('previous_status') or 'Sin estado anterior'} → {row.get('status') or 'Sin estado registrado'}",
            legacy=not bool(row.get("revision_id") or row.get("run_id") or row.get("id")),
            ref="claims", details={"previous_status": row.get("previous_status"), "status": row.get("status"), "sequence": index})

    operation_rows = [row for row in operations if isinstance(row, Mapping)]
    operation_ids = {str(row.get("operation_id") or row.get("id") or "") for row in operation_rows}
    resolution_operations: dict[str, list[Mapping[str, Any]]] = {}
    for operation in operation_rows:
        oid = str(operation.get("operation_id") or operation.get("id") or "")
        result = operation.get("result") if isinstance(operation.get("result"), Mapping) else {}
        scientific = result.get("scientific_resolution") if isinstance(result, Mapping) else None
        if isinstance(scientific, Mapping) and scientific.get("resolution_id") and oid:
            resolution_id = str(scientific["resolution_id"])
            resolution_operations.setdefault(resolution_id, []).append(operation)
        if operation.get("kind") not in (None, "claim_research"):
            continue
        if operation.get("claim_id") != claim_id:
            continue
        if not oid:
            continue
        inputs = operation.get("input_data") if isinstance(operation.get("input_data"), Mapping) else {}
        requested = operation.get("requested_at") or operation.get("created_at")
        add("automatic_investigation", "requested", requested, "claim_research.operation", oid,
            "Investigación automática solicitada", str(operation.get("evidence_mode") or inputs.get("evidence_mode") or "Modo no registrado"),
            operation_id=oid, legacy=not bool(operation.get("requested_at") or operation.get("created_at")), ref="operations",
            details={"status": operation.get("status"), "evidence_mode": operation.get("evidence_mode") or inputs.get("evidence_mode"),
                     "document_ids": operation.get("document_ids") or inputs.get("document_ids", [])})
        if operation.get("started_at"):
            add("automatic_investigation", "started", operation.get("started_at"), "claim_research.operation", oid,
                "Investigación automática iniciada", str(operation.get("stage") or ""), operation_id=oid, ref="operations")
        attempts = operation.get("attempt_history") or []
        status = str(operation.get("status") or operation.get("engine_status") or "")
        latest_attempt_number = max((int(row.get("number") or 0) for row in attempts if isinstance(row, Mapping)
                                     and str(row.get("number") or "").isdigit()), default=0)
        for attempt in attempts:
            try:
                attempt_number = int(attempt.get("number") or 0) if isinstance(attempt, Mapping) else 0
            except (TypeError, ValueError):
                attempt_number = 0
            if not isinstance(attempt, Mapping):
                continue
            if attempt_number > 1:
                add("automatic_investigation", "retry", attempt.get("started_at") or attempt.get("requested_at"),
                    "claim_research.operation.attempt", f"{oid}:{attempt.get('number')}",
                    "Se reintentó la investigación", f"Intento {attempt.get('number')} · se conservan la identidad y los checkpoints de la operación.",
                    operation_id=oid, ref="operations", details={"attempt": attempt.get("number")})
            attempt_status = str(attempt.get("status") or "")
            attempt_terminal = attempt_status in {"done", "resolved", "completed_with_limits", "failed", "error", "cancelled"}
            current_terminal = (attempt_number == latest_attempt_number and attempt_status == status
                                and attempt.get("finished_at") and attempt.get("finished_at") == operation.get("finished_at"))
            if attempt_terminal and not current_terminal:
                failed = attempt_status in {"failed", "error"}
                title = f"Intento {attempt_number} fallido" if failed else f"Intento {attempt_number} terminado"
                attempt_error = attempt.get("error")
                add("automatic_investigation", "attempt_failed" if failed else "attempt_completed",
                    attempt.get("finished_at"), "claim_research.operation.attempt",
                    f"{oid}:attempt:{attempt_number}:{attempt_status}", title,
                    str((attempt_error.get("message") if isinstance(attempt_error, Mapping) else attempt_error)
                        or attempt_status), operation_id=oid, legacy=not bool(attempt.get("finished_at")),
                    ref="operations", details={"attempt": attempt_number, "status": attempt_status,
                                                "error": attempt_error})
        if status in {"done", "resolved", "completed_with_limits", "failed", "error", "cancelled"}:
            finished = operation.get("finished_at")
            labels = {"done": "Investigación completada", "resolved": "Investigación resuelta",
                      "completed_with_limits": "Investigación completada con límites",
                      "failed": "Investigación fallida", "error": "Investigación fallida", "cancelled": "Investigación cancelada"}
            error = operation.get("error") or operation.get("engine_error") or operation.get("frontend_error")
            add("automatic_investigation", status, finished, "claim_research.operation", oid,
                labels.get(status, "Investigación terminada"),
                str((error.get("message") if isinstance(error, Mapping) else error) or operation.get("stage") or "Resultado conservado"),
                operation_id=oid, legacy=not bool(finished), ref="operations",
                details={"status": status, "stage": operation.get("stage"), "error": error})

    # Old projections are retained if their operation was not available.
    for row in claim.get("automatic_research_history") or []:
        if not isinstance(row, Mapping):
            continue
        oid = str(row.get("operation_id") or "")
        if oid and oid in operation_ids:
            continue
        source_id = oid or hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        add("automatic_investigation", str(row.get("outcome") or "completed"), row.get("finished_at"),
            "automatic_research_history", source_id, "Investigación automática histórica",
            str(row.get("outcome") or "Resultado histórico conservado"), operation_id=oid or None,
            legacy=True, ref="claims")

    for row in revisions:
        if not isinstance(row, Mapping) or row.get("claim_id") != claim_id or not row.get("id"):
            continue
        add("automatic_investigation", "supervised_reevaluation", row.get("submitted_at"),
            "revisions.request", row["id"], "Reevaluación supervisada solicitada",
            "Material aportado para revisión manual del flujo; no se confunde con una claim_research.",
            legacy=True, ref="claims", details={"status":row.get("status"), "updated_at":row.get("updated_at"),
                "error":row.get("error"), "new_status":row.get("new_status")})
        if row.get("updated_at") and row.get("updated_at") != row.get("submitted_at"):
            status = str(row.get("status") or "sin estado")
            add("automatic_investigation", "supervised_reevaluation_status", row.get("updated_at"),
                "revisions.status", f"{row['id']}:status:{status}", "Estado de reevaluación supervisada",
                str(row.get("error") or row.get("new_status") or status), legacy=False, ref="claims",
                details={"status": status, "error": row.get("error"), "new_status": row.get("new_status")})

    resolution_rows = list(claim.get("scientific_resolution_history") or [])
    for operation in operation_rows:
        result = operation.get("result") if isinstance(operation.get("result"), Mapping) else {}
        scientific = result.get("scientific_resolution") if isinstance(result, Mapping) else None
        if isinstance(scientific, Mapping) and scientific.get("resolution_id") and not any(
                isinstance(row, Mapping) and row.get("resolution_id") == scientific.get("resolution_id") for row in resolution_rows):
            resolution_rows.append(scientific)
    latest_resolution = claim.get("scientific_resolution")
    if isinstance(latest_resolution, Mapping) and not any(
            isinstance(row, Mapping) and row.get("resolution_id") == latest_resolution.get("resolution_id") for row in resolution_rows):
        resolution_rows.append(latest_resolution)
    seen_resolutions: set[str] = set()
    for row in resolution_rows:
        if not isinstance(row, Mapping):
            continue
        rid = str(row.get("resolution_id") or "")
        if not rid or rid in seen_resolutions:
            continue
        seen_resolutions.add(rid)
        candidates = sorted(resolution_operations.get(rid, []),
                            key=lambda operation: str(operation.get("operation_id") or operation.get("id") or ""))
        associated = next((operation for operation in candidates
                           if str(operation.get("operation_id") or operation.get("id") or "") == str(row.get("operation_id") or "")), None)
        if associated is None and not row.get("operation_id") and len(candidates) == 1:
            associated = candidates[0]
        oid = row.get("operation_id") or (associated.get("operation_id") or associated.get("id") if associated else None)
        operation_inputs = associated.get("input_data") if associated and isinstance(associated.get("input_data"), Mapping) else {}
        resolution = row.get("resolution") or row.get("status") or "sin clasificar"
        evidence_links: set[tuple[str, str]] = set()
        dimensions = row.get("dimensions") if isinstance(row.get("dimensions"), Mapping) else {}
        for dimension in dimensions.values():
            if not isinstance(dimension, Mapping):
                continue
            for evidence_id in dimension.get("evidence_ids") or dimension.get("passage_ids") or []:
                if evidence_id:
                    evidence_links.add(("", str(evidence_id)))
            for evidence in dimension.get("evidence") or []:
                if isinstance(evidence, Mapping) and evidence.get("evidence_id"):
                    evidence_links.add((str(evidence.get("source_id") or ""), str(evidence["evidence_id"])))
        linked_evidence = [{"source_id": source_id or None, "evidence_id": evidence_id}
                           for source_id, evidence_id in sorted(evidence_links)]
        claim_version = row.get("claim_version")
        if claim_version is None and associated:
            claim_version = associated.get("claim_version")
        if claim_version is None:
            claim_version = operation_inputs.get("claim_version")
        input_fingerprint = row.get("input_fingerprint")
        if not input_fingerprint and associated:
            input_fingerprint = associated.get("input_fingerprint")
        if not input_fingerprint:
            input_fingerprint = operation_inputs.get("input_fingerprint")
        add("scientific_resolution", "recorded", row.get("created_at"), "scientific_resolution_history", rid,
            "Resolución científica registrada", str(resolution), operation_id=oid, legacy=not bool(row.get("created_at")),
            ref="claims", details={"resolution": resolution, "limitations": row.get("limitations") or row.get("limits"),
                                   "dimensions": dimensions,
                                   "input_fingerprint": input_fingerprint,
                                   "claim_version": claim_version,
                                   "evidence_links": linked_evidence,
                                   "evidence_ids": sorted({evidence_id for _, evidence_id in evidence_links}),
                                   "resolution_id": rid})

    # Technical checks enter this projection only through an explicit claim association.
    for operation in operation_rows:
        oid = str(operation.get("operation_id") or operation.get("id") or "")
        result = operation.get("result") if isinstance(operation.get("result"), Mapping) else {}
        inputs = operation.get("input_data") if isinstance(operation.get("input_data"), Mapping) else {}
        associated=(operation.get("claim_id") == claim_id or claim_id in (inputs.get("claim_ids") or []))
        if operation.get("kind") != "technical_check" or not associated:
            continue
        status=str(operation.get("status") or "")
        add("technical_source_check", "requested", operation.get("requested_at") or operation.get("created_at"),
            "technical_check.operation", oid, "Comprobación técnica solicitada",
            "Comprueba acceso y recuperación de pasajes; no busca estudios ni cambia el veredicto.",
            operation_id=oid, legacy=not bool(operation.get("requested_at") or operation.get("created_at")),
            ref="sources", details={"status":status})
        if status in {"done","failed","error","cancelled"}:
            error=operation.get("error") or operation.get("engine_error") or operation.get("frontend_error")
            add("technical_source_check", status, operation.get("finished_at"), "technical_check.operation", oid,
                "Comprobación técnica terminada" if status=="done" else "Comprobación técnica fallida",
                str((error.get("message") if isinstance(error, Mapping) else error) or "Resultado técnico guardado; el veredicto se conserva."),
                operation_id=oid, legacy=not bool(operation.get("finished_at")), ref="sources",
                details={"status":status,"error":error})
        if not isinstance(result, Mapping):
            continue
        for receipt in result.get("source_receipts") or []:
            if not isinstance(receipt, Mapping) or receipt.get("claim_id") != claim_id:
                continue
            sid = receipt.get("source_check_id")
            if not sid:
                continue
            add("technical_source_check", "checked", receipt.get("checked_at") or operation.get("finished_at"),
                "technical_check.source_receipt", sid, "Comprobación técnica de fuente",
                str(receipt.get("availability") or "Resultado técnico registrado") +
                (" · el pasaje se localizó" if receipt.get("excerpt_match") else " · el pasaje no quedó confirmado"),
                operation_id=oid, legacy=not bool(receipt.get("checked_at")), ref="sources",
                details={"availability": receipt.get("availability"), "excerpt_match": receipt.get("excerpt_match"),
                         "eligible": receipt.get("eligible"), "source_id": receipt.get("source_id")})
    for receipt in legacy_source_checks:
        if not isinstance(receipt, Mapping) or not receipt.get("source_check_id"):
            continue
        add("technical_source_check", "checked", receipt.get("checked_at"), "claim.evidence.source_check_id",
            receipt["source_check_id"], "Comprobación técnica de fuente histórica",
            str(receipt.get("availability") or "Resultado técnico conservado"), legacy=True, ref="sources",
            details={"availability": receipt.get("availability"), "excerpt_match": receipt.get("excerpt_match"),
                     "eligible": receipt.get("eligible")})

    for row in human_reviews:
        if not isinstance(row, Mapping) or row.get("claim_id") != claim_id or not row.get("id"):
            continue
        evidence_refs = []
        for item in row.get("examined_evidence") or []:
            if not isinstance(item, Mapping):
                continue
            evidence = item.get("evidence") if isinstance(item.get("evidence"), Mapping) else {}
            ref = {"index": item.get("index")}
            for key in ("source_id", "evidence_id", "document_id", "type", "url", "path", "ref",
                        "page", "physical_page", "printed_page", "section", "location"):
                value = evidence.get(key)
                if value is not None and value != "":
                    ref[key] = value
            evidence_refs.append(ref)
        add("human_review", "recorded", row.get("reviewed_at"), "human_review", row["id"],
            "Revisión humana registrada", str(row.get("actor") or "Actor no declarado") + " · " + str(row.get("decision") or "Sin decisión"),
            legacy=not bool(row.get("reviewed_at")), ref="claims", details={"actor": row.get("actor"), "decision": row.get("decision"),
                "notes": row.get("notes"), "limits": row.get("limits"), "claim_fingerprint": row.get("claim_fingerprint"),
                "claim_version": row.get("claim_version"),
                "automatic_status_at_review": row.get("automatic_status_at_review"),
                "automatic_verdict_changed": False, "examined_evidence": row.get("examined_evidence"),
                "examined_evidence_refs": evidence_refs})

    for row in reformulations:
        if not isinstance(row, Mapping):
            continue
        parent = row.get("parent_claim_id")
        child = row.get("revised_claim_id")
        if claim_id not in (parent, child):
            continue
        proposal_id = row.get("id")
        if not proposal_id:
            continue
        status = str(row.get("status") or "proposed")
        approved = status == "approved"
        rejected = status in {"rejected", "declined", "dismissed"}
        is_child = claim_id == child
        # A proposal belongs to the parent. The child only exists once the
        # proposal is approved, so never project the earlier proposal onto it.
        if is_child and not approved:
            continue
        occurred_at = (row.get("approved_at") if approved else
                       row.get("rejected_at") if rejected else row.get("created_at"))
        add("claim_reformulation", "approved" if approved else "rejected" if rejected else "proposed",
            occurred_at,
            "claim_reformulation_history", f"{proposal_id}:{'child' if is_child else 'parent'}:{row.get('status')}",
            "Claim descendiente creado" if is_child and approved else ("Reformulación aprobada" if approved else "Propuesta de reformulación rechazada" if rejected else "Reformulación propuesta"),
            str(row.get("revised_claim") or row.get("reason") or "Formulación original preservada"),
            legacy=not bool(occurred_at), ref="claims",
            details={"proposal_id": proposal_id, "parent_claim_id": parent, "child_claim_id": child,
                     "retained_dimensions": row.get("retained_dimensions"), "reason": row.get("reason"),
                     "actor": row.get("approved_by") or row.get("rejected_by") or row.get("actor"),
                     "status": status, "evidence_inherited": False, "verdict_inherited": False})

    for decision in scope_history:
        if not isinstance(decision, Mapping) or decision.get("status") != "approved":
            continue
        if claim_id not in (decision.get("selected_ids") or []):
            continue
        source_id = decision.get("id")
        if not source_id:
            continue
        add("claim", "admitted_to_scope", decision.get("approved_at"), "scope_history", source_id,
            "Hipótesis admitida al alcance", str(decision.get("decision_reason") or "Alcance aprobado; esto no verifica la hipótesis."),
            legacy=not bool(decision.get("approved_at")), ref="question")

    for receipt in claim.get("execution_receipts") or []:
        if not isinstance(receipt, Mapping) or not receipt.get("run_id") or not receipt.get("stage"):
            continue
        status = str(receipt.get("status") or "unknown")
        title = ("Recopilación" if receipt.get("stage") == "pass2" else "Revisión crítica") + " · " + (
            "Proveedor terminó" if status == "provider_completed" else "Llamada fallida")
        elapsed = receipt.get("elapsed_seconds")
        duration = f"{elapsed} segundos" if elapsed is not None else "Duración no registrada"
        summary = (duration + ". " + ("Recopilación anterior reutilizada. " if receipt.get("reused") else "")
                   + "La finalización del proveedor no certifica el veredicto.")
        add("automatic_investigation", "tool_receipt", receipt.get("finished_at"),
            "action_trace.receipt", f"{receipt['run_id']}:{receipt['stage']}", title, summary,
            legacy=not bool(receipt.get("finished_at")), ref="claims",
            details={"run_id": receipt["run_id"], "stage": receipt["stage"], "status": status,
                     "elapsed_seconds": elapsed, "reused": bool(receipt.get("reused"))})

    return sorted(events, key=lambda row: (*_time_key(row.get("occurred_at")),
                                           row["category"], row["source_record_id"], row["event"]))


_EVENT_TYPES = {
    ("claim", "created"): "claim.created",
    ("claim", "admitted_to_scope"): "claim.admitted",
    ("verdict_change", "changed"): "evaluation.changed",
    ("automatic_investigation", "requested"): "investigation.requested",
    ("automatic_investigation", "started"): "investigation.started",
    ("automatic_investigation", "retry"): "investigation.retry",
    ("scientific_resolution", "recorded"): "scientific_resolution.recorded",
    ("technical_source_check", "requested"): "technical_check.requested",
    ("technical_source_check", "done"): "technical_check.completed",
    ("technical_source_check", "failed"): "technical_check.failed",
    ("technical_source_check", "error"): "technical_check.failed",
    ("technical_source_check", "cancelled"): "technical_check.cancelled",
    ("technical_source_check", "checked"): "technical_check.source_checked",
    ("document", "associated"): "document.associated",
    ("human_review", "recorded"): "human_review.recorded",
    ("claim_reformulation", "proposed"): "reformulation.proposed",
    ("claim_reformulation", "approved"): "reformulation.approved",
    ("claim_reformulation", "rejected"): "reformulation.rejected",
    ("automatic_investigation", "attempt_completed"): "investigation.attempt_completed",
    ("automatic_investigation", "attempt_failed"): "investigation.attempt_failed",
    ("automatic_investigation", "tool_receipt"): "investigation.tool_receipt",
    ("automatic_investigation", "supervised_reevaluation"): "supervised_reevaluation.requested",
    ("automatic_investigation", "supervised_reevaluation_status"): "supervised_reevaluation.status_changed",
}


def _event_type(row: Mapping[str, Any]) -> str:
    category, event = str(row.get("category") or ""), str(row.get("event") or "")
    details = row.get("details") if isinstance(row.get("details"), Mapping) else {}
    if (category == "claim_reformulation" and event == "approved"
            and details.get("child_claim_id") == row.get("claim_id")):
        return "claim.child_created"
    known = _EVENT_TYPES.get((category, event))
    if known:
        return known
    if category == "automatic_investigation":
        if event in {"done", "resolved", "completed_with_limits"}:
            return "investigation.completed"
        if event in {"failed", "error"}:
            return "investigation.failed"
        if event == "cancelled":
            return "investigation.cancelled"
    return f"{category}.{event}" if category and event else "record.unknown"


def _canonical_timestamp(value: Any) -> str | None:
    """Expose only explicit timezone-aware timestamps as canonical timeline time."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return None
    return value if parsed.tzinfo is not None else None


def case_activity_event(case_id: str, *, record_type: str, record_id: str,
                        event_type: str, timestamp: Any, title: str, summary: str = "",
                        claim_id: str | None = None, target_view: str = "overview",
                        tone: str = "info", sequence: int = 0) -> dict[str, Any] | None:
    """Create a stable activity DTO for a persisted case-level record.

    The caller must provide an identity already present in, or deterministically
    derived from, the persisted record. Missing identities are omitted rather
    than replaced with a timestamp, list position, or random value.
    """
    if not case_id or not record_type or not record_id or not event_type:
        return None
    occurred_at = _canonical_timestamp(timestamp)
    text = f"{title}: {summary}" if summary else title
    return {
        "event_id": _event_id(f"case_activity:{record_type}", case_id, str(record_id), event_type),
        "event_type": event_type,
        "timestamp": occurred_at,
        "occurred_at": occurred_at,
        "category": "case_activity",
        "event": event_type,
        "source_record_type": record_type,
        "source_record_id": str(record_id),
        "claim_id": claim_id,
        "title": str(title or ""),
        "summary": str(summary or ""),
        "text": text,
        "target_view": target_view,
        "tone": tone,
        "sequence": sequence if isinstance(sequence, int) and not isinstance(sequence, bool) else 0,
        "legacy": occurred_at is None,
    }


def project_case_activity(claim_timelines: Iterable[Iterable[Mapping[str, Any]]],
                          case_events: Iterable[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    """Merge canonical claim timelines with persisted case-level activity.

    Claim events are consumed as already projected; this only composes and
    applies the exact same deterministic ordering contract. Event identity is
    the sole deduplication key, so refreshing the same snapshot is idempotent.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for collection in (*list(claim_timelines), list(case_events)):
        for source in collection:
            if not isinstance(source, Mapping):
                continue
            event_id = source.get("event_id")
            if not isinstance(event_id, str) or not event_id.strip():
                continue
            row = dict(source)
            # Claim timeline events need to open a real UI destination. Add only
            # navigation metadata during composition; the canonical event
            # identity, timestamp, content and ordering fields stay untouched.
            if row.get("claim_id") and not row.get("target_view"):
                row["target_view"] = "claims"
            timestamp = _canonical_timestamp(row.get("timestamp", row.get("occurred_at")))
            row["timestamp"] = timestamp
            row.setdefault("occurred_at", timestamp)
            row.setdefault("event_type", _event_type(row))
            row.setdefault("text", f"{row.get('title') or ''}: {row.get('summary') or ''}".rstrip(": "))
            sequence = row.get("sequence", 0)
            row["sequence"] = sequence if isinstance(sequence, int) and not isinstance(sequence, bool) else 0
            row["source_record_id"] = str(row.get("source_record_id") or "")
            previous = by_id.get(event_id)
            if previous is not None and previous != row:
                raise ValueError(f"Evento de actividad con identidad duplicada pero contenido distinto: {event_id}")
            by_id[event_id] = row
    return sorted(by_id.values(), key=lambda row: (
        *_time_key(row.get("timestamp")),
        str(row.get("event_type") or ""),
        str(row.get("source_record_id") or ""),
        row["sequence"],
        str(row.get("event_id") or ""),
    ))


def project_claim_timeline(claim: Mapping[str, Any], *, operations: Iterable[Mapping[str, Any]] = (),
                           human_reviews: Iterable[Mapping[str, Any]] = (),
                           reformulations: Iterable[Mapping[str, Any]] = (),
                           scope_history: Iterable[Mapping[str, Any]] = (),
                           legacy_source_checks: Iterable[Mapping[str, Any]] = (),
                           revisions: Iterable[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    """Return the canonical, deterministic DTO projection of persisted claim records.

    This function is pure: callers load records, while this projector neither
    accesses storage nor mutates source rows. The previous display fields stay
    available as aliases during the frontend transition.
    """
    legacy_rows = _build_claim_timeline_legacy_dto(
        claim, operations=operations, human_reviews=human_reviews,
        reformulations=reformulations, scope_history=scope_history,
        legacy_source_checks=legacy_source_checks, revisions=revisions)
    canonical: list[dict[str, Any]] = []
    for row in legacy_rows:
        details = row.get("details") if isinstance(row.get("details"), Mapping) else {}
        persisted_sequence = details.get("sequence")
        sequence = (persisted_sequence if isinstance(persisted_sequence, int)
                    and not isinstance(persisted_sequence, bool) else 0)
        title = str(row.get("title") or "")
        summary = str(row.get("summary") or "")
        human_text = f"{title}: {summary}" if summary else title
        canonical.append({**row,
            "timestamp": _canonical_timestamp(row.get("occurred_at")),
            "event_type": _event_type(row),
            "text": human_text,
            # Zero means this record has no persisted sequence. Stable IDs and
            # event_type provide the tie-break; it does not imply chronology.
            "sequence": sequence,
        })

    canonical.sort(key=lambda row: (*_time_key(row.get("timestamp")),
                                    row["event_type"], row["source_record_id"],
                                    row["sequence"], row["event_id"]))
    return canonical


def build_claim_timeline(claim: Mapping[str, Any], *, operations: Iterable[Mapping[str, Any]] = (),
                         human_reviews: Iterable[Mapping[str, Any]] = (),
                         reformulations: Iterable[Mapping[str, Any]] = (),
                         scope_history: Iterable[Mapping[str, Any]] = (),
                         legacy_source_checks: Iterable[Mapping[str, Any]] = (),
                         revisions: Iterable[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    """Backward-compatible name for the canonical claim timeline projector."""
    return project_claim_timeline(
        claim, operations=operations, human_reviews=human_reviews,
        reformulations=reformulations, scope_history=scope_history,
        legacy_source_checks=legacy_source_checks, revisions=revisions)
