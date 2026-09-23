"""Contracts and validation for the specialized research agents.

The orchestration layer accepts an injected provider.  Nothing in this module
contacts a model or the network, which keeps automated tests and dry runs safe.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping


ROLES = (
    "planner", "formulation_reviewer", "locator", "retriever",
    "source_evaluator", "relevance_evaluator", "skeptic", "writer",
    "final_auditor",
)
DIMENSIONS = ("intervention", "spacing", "comparison", "population", "material", "outcome", "horizon")
RELATIONS = {"supports", "contradicts", "mismatch", "unreported"}
IDENTITY_STATUSES = {"confirmed", "uncertain"}
CREDIBILITY_STATUSES = {"credible", "uncertain", "not_credible"}
PRIMARY_STATUSES = {"confirmed_primary", "declared_primary", "secondary", "uncertain"}
INDEPENDENCE_STATUSES = {"provider_assessed_independent", "duplicate", "not_established"}
ACCESS_STATUSES = {"available", "restricted", "local"}
VERDICTS = {"VERIFIED", "PARTIAL", "UNSUPPORTED", "CONTRADICTED"}
AUDIT_DECISIONS = {"sufficient_support", "direct_contradiction", "continue", "exhausted"}


class AgentOutputError(ValueError):
    """The provider returned an incomplete or unsafe agent result."""


def stable_digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AgentOutputError(f"{label} debe ser un objeto JSON.")
    return value


def _text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise AgentOutputError(f"{label} debe contener texto.")
    return value.strip()


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AgentOutputError(f"{label} debe ser una lista.")
    return value


def _source_id(row: Mapping[str, Any], label: str) -> str:
    return _text(row.get("source_id"), f"{label}.source_id")


def validate_agent_output(role: str, value: Any) -> dict[str, Any]:
    """Validate and return a detached JSON-compatible result."""
    if role not in ROLES:
        raise AgentOutputError(f"Agente desconocido: {role}")
    data = dict(_mapping(value, role))
    if role == "planner":
        matrix = _mapping(data.get("matrix"), "planner.matrix")
        for key in DIMENSIONS:
            _text(matrix.get(key), f"planner.matrix.{key}", allow_empty=True)
        _list(data.get("gaps"), "planner.gaps")
        for key in ("competing_hypotheses", "falsification_criteria", "retrieval_targets"):
            _list(data.get(key), f"planner.{key}")
        for index, row in enumerate(data["retrieval_targets"]):
            row = _mapping(row, f"planner.retrieval_targets[{index}]")
            dimensions = _list(row.get("dimension_ids"), f"planner.retrieval_targets[{index}].dimension_ids")
            if not dimensions or any(value not in DIMENSIONS for value in dimensions):
                raise AgentOutputError("Cada objetivo de recuperación debe señalar dimensiones conocidas.")
            _text(row.get("query"), f"planner.retrieval_targets[{index}].query")
            if row.get("purpose") not in {"support", "contradiction", "identity_recovery"}:
                raise AgentOutputError("planner.retrieval_targets.purpose es inválido.")
        critical={key for key,value in matrix.items() if value}
        contradictory={dimension for row in data['retrieval_targets'] if row.get('purpose')=='contradiction'
                       for dimension in row.get('dimension_ids',[])}
        if critical and not critical.issubset(contradictory):
            raise AgentOutputError("Cada dimensión declarada debe tener una búsqueda explícita de contradicción.")
    elif role == "formulation_reviewer":
        if not isinstance(data.get("compound"), bool):
            raise AgentOutputError("formulation_reviewer.compound debe ser booleano.")
        questions = _list(data.get("subquestions"), "formulation_reviewer.subquestions")
        if len(questions) > 2:
            raise AgentOutputError("Sólo se permiten dos subpreguntas.")
        for index, row in enumerate(questions):
            row = _mapping(row, f"subquestions[{index}]")
            _text(row.get("id"), f"subquestions[{index}].id")
            _text(row.get("claim"), f"subquestions[{index}].claim")
            if row.get("within_scope") is not True:
                raise AgentOutputError("Toda subpregunta automática debe permanecer dentro del alcance.")
            dimensions = _list(row.get("dimension_ids"), f"subquestions[{index}].dimension_ids")
            if not dimensions or any(value not in DIMENSIONS for value in dimensions):
                raise AgentOutputError("Cada subpregunta debe indicar las dimensiones que examina.")
    elif role == "locator":
        for index, row in enumerate(_list(data.get("candidates"), "locator.candidates")):
            row = _mapping(row, f"candidates[{index}]")
            _text(row.get("query"), f"candidates[{index}].query")
            if not any(isinstance(row.get(k), str) and row[k].strip() for k in ("url", "doi", "pmid", "document_id")):
                raise AgentOutputError("Cada candidato necesita un identificador recuperable.")
            if not isinstance(row.get('dimension_ids'),list) or not row['dimension_ids'] or any(d not in DIMENSIONS for d in row['dimension_ids']):
                raise AgentOutputError("Cada candidato debe quedar relacionado con dimensiones del hueco buscado.")
            if row.get('purpose') not in {'support','contradiction','identity_recovery'}:
                raise AgentOutputError("Cada candidato debe declarar el propósito de recuperación.")
    elif role == "retriever":
        for index, row in enumerate(_list(data.get("sources"), "retriever.sources")):
            row = _mapping(row, f"sources[{index}]")
            _source_id(row, f"sources[{index}]")
            origin = row.get("source_identity_origin")
            if origin is not None and origin not in {"supplied", "wrapper_existing_policy"}:
                raise AgentOutputError("retriever.source_identity_origin es inválido.")
            identity_policy = row.get("source_identity_policy")
            if identity_policy is not None and identity_policy != "source-identity-v1":
                raise AgentOutputError("retriever.source_identity_policy es inválida.")
            if origin == "wrapper_existing_policy":
                basis = row.get("source_identity_basis")
                if identity_policy == "source-identity-v1":
                    identity_key = _text(row.get("source_identity_key"), "retriever.source_identity_key")
                    if hashlib.sha256(identity_key.encode("utf-8")).hexdigest() != row.get("source_id"):
                        raise AgentOutputError("retriever.source_identity_key no coincide con source_id.")
                    signals = _list(row.get("source_identity_signals"), "retriever.source_identity_signals")
                    if not signals or any(not isinstance(signal, str) or not signal.strip() for signal in signals):
                        raise AgentOutputError("retriever.source_identity_signals debe registrar señales estables.")
                elif (basis != "authorized_document_id" or row.get("document_id") != row.get("source_id")
                      or not row.get("source_identity_signals")):
                    raise AgentOutputError("La identidad local normalizada debe corresponder al documento autorizado.")
            passages = _list(row.get("passages"), f"sources[{index}].passages")
            if not passages:
                raise AgentOutputError("Una fuente recuperada necesita al menos un pasaje.")
            for pindex, passage in enumerate(passages):
                passage = _mapping(passage, f"passages[{pindex}]")
                _text(passage.get("evidence_id"), "passage.evidence_id")
                _text(passage.get("excerpt"), "passage.excerpt")
                if not any(passage.get(k) not in (None, "") for k in ("page", "section", "location")):
                    raise AgentOutputError("Cada pasaje necesita una ubicación comprobable.")
    elif role == "source_evaluator":
        for index, row in enumerate(_list(data.get("assessments"), "source_evaluator.assessments")):
            row = _mapping(row, f"assessments[{index}]")
            _source_id(row, f"assessments[{index}]")
            enums=(("identity_status",IDENTITY_STATUSES),("credibility_status",CREDIBILITY_STATUSES),
                   ("primary_status",PRIMARY_STATUSES),("independence_status",INDEPENDENCE_STATUSES),
                   ("access",ACCESS_STATUSES))
            for key,allowed in enums:
                if row.get(key) not in allowed:
                    raise AgentOutputError(f"source_evaluator.{key} es inválido.")
            for key in ("credibility_basis","primary_basis","independence_basis"):
                _text(row.get(key),f"source_evaluator.{key}")
    elif role == "relevance_evaluator":
        rows = _list(data.get("matrix"), "relevance_evaluator.matrix")
        for index, row in enumerate(rows):
            row = _mapping(row, f"matrix[{index}]")
            _source_id(row, f"matrix[{index}]")
            _text(row.get("evidence_id"), f"matrix[{index}].evidence_id")
            dimensions = _mapping(row.get("dimensions"), f"matrix[{index}].dimensions")
            for key in DIMENSIONS:
                if dimensions.get(key) not in RELATIONS:
                    raise AgentOutputError(f"Relación inválida para {key}.")
            if row.get("overall_relation") not in RELATIONS:
                raise AgentOutputError("relevance_evaluator.overall_relation es inválida.")
            _text(row.get("basis"),f"matrix[{index}].basis")
    elif role == "skeptic":
        if data.get("verdict") not in VERDICTS:
            raise AgentOutputError("Veredicto crítico inválido.")
        _text(data.get("rationale"), "skeptic.rationale")
        _text(data.get("contradiction_search"), "skeptic.contradiction_search")
        _list(data.get("support_source_ids"), "skeptic.support_source_ids")
    elif role == "writer":
        for key in ("summary", "what_found", "limits", "unanswered"):
            _text(data.get(key), f"writer.{key}", allow_empty=(key == "unanswered"))
    elif role == "final_auditor":
        if data.get("decision") not in AUDIT_DECISIONS:
            raise AgentOutputError("Decisión de auditoría inválida.")
        _text(data.get("explanation"), "final_auditor.explanation")
        _list(data.get("errors"), "final_auditor.errors")
        unresolved = data.get("unresolved_dimensions", [])
        if not isinstance(unresolved, list) or any(value not in DIMENSIONS for value in unresolved):
            raise AgentOutputError("final_auditor.unresolved_dimensions es inválido.")
        criteria = _list(data.get("indeterminacy_criteria", []), "final_auditor.indeterminacy_criteria")
        if any(not isinstance(value, str) or not value.strip() for value in criteria):
            raise AgentOutputError("Los criterios de indeterminación deben ser explicaciones comprobables.")
    # Round trip rejects non-JSON objects and detaches provider-owned data.
    try:
        return json.loads(json.dumps(data, ensure_ascii=False))
    except (TypeError, ValueError) as exc:
        raise AgentOutputError("La salida no es JSON válido.") from exc


@dataclass(frozen=True)
class AgentCall:
    role: str
    payload: dict[str, Any]
    manifest: dict[str, Any]


Provider = Callable[[AgentCall], Mapping[str, Any] | Iterable[Mapping[str, Any]]]


def role_skill_name(role: str) -> str:
    return "research-" + re.sub(r"_", "-", role)
