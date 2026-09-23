"""Persistent, bounded orchestration for automatic claim research.

This module is deliberately disconnected from the current frontend and live
case library.  A later adapter may expose it through HTTP after isolated tests.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from research_agents import AgentCall, AgentOutputError, DIMENSIONS, stable_digest, validate_agent_output
import source_identity


POLICY = "automatic-claim-research-v2"
PROFILE_NAME = "three-rounds-v1"
EVIDENCE_MODES = {"question_search", "documents_only", "documents_plus_search"}
ROUNDS = (
    {"number": 1, "name": "direct_primary", "query_limit": 6, "page_limit": 8},
    {"number": 2, "name": "identity_recovery", "query_limit": 4, "page_limit": 8},
    {"number": 3, "name": "gaps_contradictions", "query_limit": 6, "page_limit": 8},
)
GLOBAL_QUERY_LIMIT = 16
GLOBAL_PAGE_LIMIT = 24
GLOBAL_SECONDS_LIMIT = 30 * 60


class BudgetExceeded(RuntimeError):
    pass


class OperationConflict(RuntimeError):
    pass


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


class OperationStore:
    """Append-only artifacts plus an atomically replaced operation projection."""
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def folder(self, operation_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", operation_id):
            raise ValueError("operation_id inválido")
        return self.root / operation_id

    def create(self, case_id: str, claim_id: str, claim: str, *, evidence_mode="question_search", document_ids=None, claim_version=None) -> dict[str, Any]:
        if evidence_mode not in EVIDENCE_MODES:
            raise ValueError("Modo de evidencia inválido")
        document_ids=sorted(set(document_ids or []))
        if evidence_mode == "question_search" and document_ids:
            raise ValueError("question_search no admite documentos asociados")
        if evidence_mode != "question_search" and not document_ids:
            raise ValueError("Selecciona documentos para este modo de evidencia")
        input_fingerprint=stable_digest({"claim_id":claim_id,"claim":claim,"claim_version":claim_version,
            "evidence_mode":evidence_mode,"document_ids":document_ids,"dimension_schema":1})
        operation_id = uuid.uuid4().hex
        record = {
            "policy": POLICY, "operation_id": operation_id, "kind": "claim_research",
            "case_id": case_id, "claim_id": claim_id, "claim": claim,
            "claim_version":claim_version,"evidence_mode":evidence_mode,"document_ids":document_ids,
            "input_fingerprint":input_fingerprint,
            "status": "queued", "stage": "queued", "profile": PROFILE_NAME,
            "created_at": utcnow(), "updated_at": utcnow(), "round": 0,
            "progress": {"queries": 0, "pages": 0, "elapsed_seconds": 0},
            "result": None, "error": None,
        }
        folder = self.folder(operation_id)
        folder.mkdir(parents=True, exist_ok=False)
        _atomic_json(folder / "input.json", {
            "policy": POLICY, "case_id": case_id, "claim_id": claim_id,
            "claim": claim, "profile": PROFILE_NAME, "created_at": record["created_at"],
            "claim_version":claim_version,"evidence_mode":evidence_mode,"document_ids":document_ids,
            "input_fingerprint":input_fingerprint,
        })
        _atomic_json(folder / "operation.json", record)
        return record

    def create_with_id(self, operation_id: str, case_id: str, claim_id: str, claim: str, **inputs) -> dict[str, Any]:
        """Create an operation with an HTTP-layer id, without replacing existing data."""
        if not re.fullmatch(r"[a-f0-9]{32}", operation_id):
            raise ValueError("operation_id inválido")
        if self.folder(operation_id).exists():
            return self.load(operation_id)
        record = self.create(case_id, claim_id, claim, **inputs)
        if record["operation_id"] == operation_id:
            return record
        generated = self.folder(record["operation_id"])
        target = self.root / operation_id
        generated.replace(target)
        record["operation_id"] = operation_id
        _atomic_json(target / "operation.json", record)
        input_record = json.loads((target / "input.json").read_text(encoding="utf-8"))
        input_record["operation_id"] = operation_id
        _atomic_json(target / "input.json", input_record)
        return record

    def load(self, operation_id: str) -> dict[str, Any]:
        return json.loads((self.folder(operation_id) / "operation.json").read_text(encoding="utf-8"))

    def update(self, operation_id: str, **changes: Any) -> dict[str, Any]:
        record = self.load(operation_id)
        record.update(changes, updated_at=utcnow())
        _atomic_json(self.folder(operation_id) / "operation.json", record)
        return record

    def artifact(self, operation_id: str, kind: str, value: Any, *, canonical: bool = True) -> dict[str, Any]:
        folder = self.folder(operation_id) / "artifacts" / kind
        folder.mkdir(parents=True, exist_ok=True)
        sequence = len(list(folder.glob("*.json"))) + 1
        envelope = {
            "policy": POLICY, "kind": kind, "sequence": sequence, "created_at": utcnow(),
            "canonical": canonical, "sha256": stable_digest(value), "value": value,
        }
        path = folder / f"{sequence:04d}-{envelope['sha256'][:12]}.json"
        _atomic_json(path, envelope)
        return {"kind": kind, "sequence": sequence, "sha256": envelope["sha256"],
                "canonical": canonical, "path": path.relative_to(self.folder(operation_id)).as_posix()}


def normalize_query(value: str) -> str:
    value = re.sub(r"[^\w\s]", " ", value.casefold(), flags=re.UNICODE)
    return " ".join(value.split())


def normalize_doi(value: str) -> str:
    value = value.strip().casefold()
    value = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", value)
    return value.rstrip("/.,; ")


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    host = (parts.hostname or "").casefold()
    port = parts.port
    netloc = host + ((":" + str(port)) if port and port not in (80, 443) else "")
    path = re.sub(r"/+", "/", parts.path).rstrip("/") or "/"
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return urlunsplit(((parts.scheme or "https").casefold(), netloc, path, query, ""))


def page_key(row: Mapping[str, Any]) -> str:
    if row.get("doi"):
        return "doi:" + normalize_doi(str(row["doi"]))
    if row.get("source_id"):
        return "source:" + str(row["source_id"]).casefold()
    if row.get("body_sha256"):
        return "body:" + str(row["body_sha256"]).casefold()
    url = row.get("final_url") or row.get("url")
    if url:
        return "url:" + normalize_url(str(url))
    return "row:" + stable_digest(row)


def page_keys(row: Mapping[str, Any]) -> set[str]:
    keys=set()
    for name,prefix,normalizer in (("doi","doi:",normalize_doi),("source_id","source:",lambda v:v.casefold()),
                                   ("body_sha256","body:",lambda v:v.casefold())):
        if row.get(name):keys.add(prefix+normalizer(str(row[name])))
    for name in ("url","final_url"):
        if row.get(name):keys.add("url:"+normalize_url(str(row[name])))
    return keys or {page_key(row)}


def _external_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parts = urlsplit(value.strip())
        if parts.scheme.casefold() not in {"http", "https"} or not parts.hostname:
            return None
        # Force malformed ports to fail here instead of during identity generation.
        _ = parts.port
        return value.strip()
    except ValueError:
        return None


def _source_identity_aliases(row: Mapping[str, Any]) -> set[str]:
    """Stable matching keys only; titles, excerpts and list positions are excluded."""
    aliases: set[str] = set()
    for field_name in ("url", "final_url"):
        url = _external_url(row.get(field_name))
        if not url:
            continue
        aliases.add("url:" + source_identity.canonical_url(url))
        identifier = source_identity.url_identifier(url)
        if identifier:
            aliases.add(identifier)
    for field_name in ("doi",):
        value = row.get(field_name)
        if isinstance(value, str):
            doi = normalize_doi(value)
            if re.fullmatch(r"10\.\d{4,9}/[^\s?#]+", doi, re.I):
                aliases.add("doi:" + doi.casefold())
    pmid = row.get("pmid")
    if isinstance(pmid, (str, int)) and re.fullmatch(r"\d+", str(pmid).strip()):
        aliases.add("pmid:" + str(pmid).strip())
    pmcid = row.get("pmcid")
    if isinstance(pmcid, str) and re.fullmatch(r"PMC\d+", pmcid.strip(), re.I):
        aliases.add("pmcid:" + pmcid.strip().upper())
    for field_name in ("document_id", "document_sha256"):
        value = row.get(field_name)
        if isinstance(value, str) and value.strip():
            aliases.add("document:" + value.strip().casefold())
    return aliases


def _normalize_retriever_identity(result: Any, candidates: Any, authorized_document_ids: Iterable[str] = ()) -> dict[str, Any]:
    """Fill only absent retriever IDs from source-identity-v1 or authorized document IDs."""
    if not isinstance(result, Mapping) or not isinstance(result.get("sources"), list):
        return dict(result) if isinstance(result, Mapping) else result
    candidate_rows = [row for row in candidates if isinstance(row, Mapping)] if isinstance(candidates, list) else []
    authorized = {str(value).strip().casefold(): str(value).strip()
                  for value in authorized_document_ids if isinstance(value, str) and value.strip()}
    normalized = dict(result)
    normalized_sources = []
    for index, original in enumerate(result["sources"]):
        if not isinstance(original, Mapping):
            normalized_sources.append(original)
            continue
        row = dict(original)
        source_id = row.get("source_id")
        if isinstance(source_id, str) and source_id.strip():
            row["source_identity_origin"] = "supplied"
            for key in ("source_identity_policy", "source_identity_basis", "source_identity_signals",
                        "source_identity_candidate"):
                row.pop(key, None)
            normalized_sources.append(row)
            continue
        if source_id is not None and not isinstance(source_id, str):
            normalized_sources.append(row)
            continue

        source_aliases = _source_identity_aliases(row)
        matches = [candidate for candidate in candidate_rows
                   if source_aliases and source_aliases.intersection(_source_identity_aliases(candidate))]

        # An authorized local document keeps the existing document_id-as-source_id convention.
        document_ids = set()
        for identity_row in [row, *matches]:
            for field_name in ("document_id", "document_sha256"):
                value = identity_row.get(field_name)
                if isinstance(value, str) and value.strip().casefold() in authorized:
                    document_ids.add(authorized[value.strip().casefold()])
        if len(document_ids) == 1:
            document_id = next(iter(document_ids))
            row.update(source_id=document_id, document_id=document_id,
                       source_identity_origin="wrapper_existing_policy",
                       source_identity_basis="authorized_document_id",
                       source_identity_signals=["document_id:" + document_id.casefold()])
            if matches:
                row["source_identity_candidate"] = stable_digest(sorted(
                    alias for candidate in matches for alias in _source_identity_aliases(candidate)))
            normalized_sources.append(row)
            continue
        if len(document_ids) > 1:
            raise AgentOutputError(
                f"La fuente recuperada {index + 1} coincide con varios documentos locales autorizados; "
                "no se puede conservar una identidad inequívoca.")

        # If the retriever omitted a URL, borrow one only from a uniquely matching locator identity.
        own_urls = [_external_url(row.get(name)) for name in ("url", "final_url")]
        own_urls = [value for value in own_urls if value]
        candidate_urls = sorted({url for candidate in matches for name in ("url", "final_url")
                                 if (url := _external_url(candidate.get(name)))})
        if not own_urls:
            if len(candidate_urls) != 1:
                raise AgentOutputError(
                    "Una fuente recuperada no tenía identidad utilizable; la ejecución se detuvo para no perder "
                    "trazabilidad. Añade una URL/DOI comprobable o un documento local autorizado.")
            identity_url = candidate_urls[0]
        else:
            identity_url = own_urls[0]

        # A DOI alias is used only when it is present in the source and the matched candidate set agrees.
        declared_dois = {alias[4:] for alias in _source_identity_aliases({"doi": row.get("doi")})
                         if alias.startswith("doi:")}
        source_url_dois = {identifier[4:] for name in ("url", "final_url")
                           if (url := _external_url(row.get(name)))
                           and (identifier := source_identity.url_identifier(url))
                           and identifier.startswith("doi:")}
        candidate_dois = {alias[4:] for candidate in matches
                          for alias in _source_identity_aliases(candidate) if alias.startswith("doi:")}
        reviewed_key = None
        if (len(candidate_dois) == 1 and matches and
                (not declared_dois or declared_dois == candidate_dois) and
                (not source_url_dois or candidate_dois.issubset(source_url_dois))):
            reviewed_key = ("doi", next(iter(candidate_dois)))
        receipt = {"final_url": _external_url(row.get("final_url")) or identity_url}
        try:
            identity = source_identity.identify({"type": "external", "url": identity_url},
                                                receipt=receipt, reviewed_key=reviewed_key)
        except (KeyError, TypeError, ValueError) as exc:
            raise AgentOutputError(
                "Una fuente recuperada no tenía identidad utilizable; la ejecución se detuvo para no perder "
                "trazabilidad. Añade una URL/DOI comprobable o un documento local autorizado.") from exc
        row.update(source_id=identity["source_id"], source_identity_origin="wrapper_existing_policy",
                   source_identity_policy=source_identity.POLICY,
                   source_identity_basis=identity["basis"],
                   source_identity_signals=identity["signals"],
                   source_identity_key=identity["identity_key"])
        if matches:
            row["source_identity_candidate"] = stable_digest(sorted(
                alias for candidate in matches for alias in _source_identity_aliases(candidate)))
        normalized_sources.append(row)
    normalized["sources"] = normalized_sources
    return normalized


def _normalize_retriever_passages(result: Any) -> dict[str, Any]:
    """Normalize only the observed, unambiguous flattened single-passage shape.

    The provider's raw response is persisted before this helper is called.  The
    canonical result still has a non-empty ``passages`` list with the same
    literal evidence ID, text, and locator; malformed explicit structures are
    rejected rather than repaired.
    """
    if not isinstance(result, Mapping) or not isinstance(result.get("sources"), list):
        return dict(result) if isinstance(result, Mapping) else result

    normalized = dict(result)
    normalized_sources = []
    changed = False
    for index, original in enumerate(result["sources"]):
        if not isinstance(original, Mapping):
            normalized_sources.append(original)
            continue
        row = dict(original)
        if "passages" in row:
            if not isinstance(row["passages"], list):
                raise AgentOutputError(
                    "La fuente recuperada no devolvió una lista estructurada de pasajes comprobables. "
                    "La salida se conservó para auditoría, pero no se usó como evidencia. "
                    f"Detalle técnico: sources[{index}].passages debe ser una lista."
                )
            normalized_sources.append(original)
            continue

        evidence_id = row.get("evidence_id")
        passage_text = row.get("passage")
        excerpt = row.get("excerpt")
        if passage_text not in (None, "") and not isinstance(passage_text, str):
            raise AgentOutputError(
                "La fuente recuperada no conserva un pasaje con estructura inequívoca "
                "(texto literal, evidence_id y ubicación); se rechazó sin fabricar evidencia. "
                f"Detalle técnico: sources[{index}].passage debe ser texto."
            )
        if excerpt not in (None, "") and not isinstance(excerpt, str):
            raise AgentOutputError(
                "La fuente recuperada no conserva un pasaje con estructura inequívoca "
                "(texto literal, evidence_id y ubicación); se rechazó sin fabricar evidencia. "
                f"Detalle técnico: sources[{index}].excerpt debe ser texto."
            )
        valid_evidence_id = isinstance(evidence_id, str) and bool(evidence_id.strip())
        valid_passage = isinstance(passage_text, str) and bool(passage_text.strip())
        valid_excerpt = isinstance(excerpt, str) and bool(excerpt.strip())
        if valid_passage and valid_excerpt and passage_text != excerpt:
            raise AgentOutputError(
                "La fuente recuperada no conserva un pasaje con estructura inequívoca "
                "(texto literal, evidence_id y ubicación); se rechazó sin fabricar evidencia. "
                f"Detalle técnico: sources[{index}] contiene passage y excerpt diferentes."
            )
        literal = excerpt if valid_excerpt else passage_text if valid_passage else None
        locator = any(row.get(key) not in (None, "") for key in ("page", "section", "location"))
        if not valid_evidence_id or literal is None or not locator:
            missing = []
            if not valid_evidence_id:
                missing.append("evidence_id no vacío")
            if literal is None:
                missing.append("texto literal en passage o excerpt")
            if not locator:
                missing.append("page, section o location")
            raise AgentOutputError(
                "La fuente recuperada no conserva un pasaje con estructura inequívoca "
                "(texto literal, evidence_id y ubicación); se rechazó sin fabricar evidencia. "
                f"Detalle técnico: sources[{index}] requiere " + ", ".join(missing) + "."
            )

        passage = {"evidence_id": evidence_id, "excerpt": literal}
        for key in ("page", "section", "location", "document_sha256", "extraction_id", "chunk_id",
                    "retrieval_method"):
            if row.get(key) not in (None, ""):
                passage[key] = row[key]
        row["passages"] = [passage]
        row["passage_structure_origin"] = "wrapper_flat_single_passage"
        row["passage_structure_policy"] = "retriever-passage-normalization-v1"
        normalized_sources.append(row)
        changed = True

    if changed:
        normalized["sources"] = normalized_sources
    return normalized


def _retriever_usage_with_ids(events: Iterable[Mapping[str, Any]], sources: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Attach normalized source IDs to matching observable page events."""
    output = [dict(event) for event in events if isinstance(event, Mapping)]
    for source in sources:
        source_aliases = page_keys(source) | _source_identity_aliases(source)
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            continue
        matches = [event for event in output if event.get("type") == "page"
                   and source_aliases.intersection(page_keys(event) | _source_identity_aliases(event))]
        if matches:
            for event in matches:
                event.setdefault("source_id", source_id)
        else:
            output.append({"type": "page", **{key: source[key] for key in
                ("url", "final_url", "doi", "source_id", "body_sha256") if source.get(key)}})
    return output


@dataclass
class BudgetLedger:
    started: float
    clock: Callable[[], float] = time.monotonic
    queries: set[str] = field(default_factory=set)
    pages: set[str] = field(default_factory=set)
    round_queries: set[str] = field(default_factory=set)
    round_pages: set[str] = field(default_factory=set)
    round_profile: Mapping[str, Any] | None = None
    page_count: int = 0
    round_page_count: int = 0

    def begin_round(self, profile: Mapping[str, Any]) -> None:
        self.round_profile = profile
        self.round_queries, self.round_pages = set(), set();self.round_page_count=0

    @property
    def elapsed(self) -> float:
        return max(0, self.clock() - self.started)

    def remaining(self) -> dict[str, int]:
        profile = self.round_profile or {"query_limit": 0, "page_limit": 0}
        return {
            "round_queries": max(0, profile["query_limit"] - len(self.round_queries)),
            "round_pages": max(0, profile["page_limit"] - self.round_page_count),
            "global_queries": max(0, GLOBAL_QUERY_LIMIT - len(self.queries)),
            "global_pages": max(0, GLOBAL_PAGE_LIMIT - self.page_count),
            "seconds": max(0, int(GLOBAL_SECONDS_LIMIT - self.elapsed)),
        }

    def observe(self, event: Mapping[str, Any]) -> dict[str, Any]:
        if self.elapsed > GLOBAL_SECONDS_LIMIT:
            raise BudgetExceeded("Se agotó el tiempo máximo de la afirmación.")
        kind = event.get("type")
        if kind == "query":
            key = normalize_query(str(event.get("query", "")))
            if not key:
                raise AgentOutputError("Evento de consulta vacío.")
            reused = key in self.queries
            if not reused:
                if len(self.queries) >= GLOBAL_QUERY_LIMIT or len(self.round_queries) >= self.round_profile["query_limit"]:
                    raise BudgetExceeded("Se agotó el presupuesto de consultas.")
                self.queries.add(key); self.round_queries.add(key)
            return {"kind": kind, "key": key, "reused": reused}
        if kind == "page":
            keys = page_keys(event);key=sorted(keys)[0]
            reused = bool(keys & self.pages)
            if not reused:
                if self.page_count >= GLOBAL_PAGE_LIMIT or self.round_page_count >= self.round_profile["page_limit"]:
                    raise BudgetExceeded("Se agotó el presupuesto de páginas.")
                self.page_count+=1;self.round_page_count+=1
            self.pages.update(keys);self.round_pages.update(keys)
            return {"kind": kind, "key": key, "reused": reused}
        return {"kind": kind or "other", "reused": False}

    def receipt(self, round_number: int, stopped_reason: str) -> dict[str, Any]:
        return {"round": round_number, "queries_new": len(self.round_queries),
                "pages_new": self.round_page_count, "queries_total": len(self.queries),
                "pages_total": self.page_count, "elapsed_seconds": round(self.elapsed, 3),
                "remaining": self.remaining(), "stopped_reason": stopped_reason}


class ResearchOrchestrator:
    """Run one bounded operation using an injected, cancellable provider."""
    def __init__(self, store: OperationStore, provider: Callable[[AgentCall], Any], *, clock=time.monotonic):
        self.store, self.provider, self.clock = store, provider, clock

    def _manifest(self, operation: Mapping[str, Any], role: str, round_profile: Mapping[str, Any] | None,
                  budget: BudgetLedger) -> dict[str, Any]:
        return {"policy": POLICY, "operation_id": operation["operation_id"],
                "claim_ids": [operation["claim_id"]], "agent": role,
                "evidence_mode":operation.get("evidence_mode","question_search"),
                "document_ids":list(operation.get("document_ids",[])),
                "input_fingerprint":operation.get("input_fingerprint"),
                "stage": "preflight" if round_profile is None else round_profile["name"],
                "round": 0 if round_profile is None else round_profile["number"],
                "budget_remaining": budget.remaining(),
                "queries_already_performed": sorted(budget.queries),
                "pages_already_retrieved": sorted(budget.pages), "created_at": utcnow()}

    def _checkpoint(self, operation_id: str, role: str, stage: str, round_number: int) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
        """Return a previously validated agent result and its observable usage.

        A retry may reuse only canonical, schema-valid output from the same
        role, stage and round. Provider output that failed parsing or
        validation is never a checkpoint.
        """
        base = self.store.folder(operation_id) / "artifacts"
        results: list[tuple[dict[str, Any], dict[str, Any], Any]] = []
        for path in sorted((base / "agent-results").glob("*.json"), reverse=True):
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
                value = envelope.get("value", {})
                manifest = value.get("manifest", {})
                if (envelope.get("canonical") is True and manifest.get("agent") == role
                        and manifest.get("stage") == stage and int(manifest.get("round", 0)) == round_number):
                    result = validate_agent_output(role, value.get("result"))
                    results.append((manifest, result, value.get("usage_events")))
                    break
            except (OSError, ValueError, TypeError, AgentOutputError):
                continue
        if not results:
            return None
        manifest, result, saved_events = results[0]
        events: list[dict[str, Any]] = [dict(row) for row in saved_events if isinstance(row, Mapping)] \
            if isinstance(saved_events, list) else []
        if saved_events is None:
            for path in sorted((base / "raw-agent-output").glob("*.json"), reverse=True):
                try:
                    value = json.loads(path.read_text(encoding="utf-8")).get("value", {})
                    raw_manifest = value.get("manifest", {})
                    if (raw_manifest.get("agent") == role and raw_manifest.get("stage") == stage
                            and int(raw_manifest.get("round", 0)) == round_number):
                        events = [dict(row) for row in value.get("events", []) if isinstance(row, Mapping)]
                        break
                except (OSError, ValueError, TypeError):
                    continue
        return result, events

    def _prior_attempt_events(self, operation_id: str, role: str, stage: str,
                              round_number: int) -> list[dict[str, Any]]:
        """Return observable events from prior noncanonical attempts of this exact call."""
        base = self.store.folder(operation_id) / "artifacts"
        events: list[dict[str, Any]] = []
        for kind in ("raw-agent-output", "raw-agent-events"):
            for path in sorted((base / kind).glob("*.json")):
                try:
                    value = json.loads(path.read_text(encoding="utf-8")).get("value", {})
                    manifest = value.get("manifest", {})
                    if (manifest.get("agent") == role and manifest.get("stage") == stage
                            and int(manifest.get("round", 0)) == round_number):
                        events.extend(dict(event) for event in value.get("events", [])
                                      if isinstance(event, Mapping))
                except (OSError, ValueError, TypeError):
                    continue
        return events

    def _call(self, operation: Mapping[str, Any], role: str, payload: dict[str, Any],
              budget: BudgetLedger, round_profile: Mapping[str, Any] | None) -> dict[str, Any]:
        stage = "preflight" if round_profile is None else round_profile["name"]
        round_number = 0 if round_profile is None else round_profile["number"]
        cached = self._checkpoint(operation["operation_id"], role, stage, round_number)
        if cached:
            result, events = cached
            for event in events:
                budget.observe(event)
            self.store.artifact(operation["operation_id"], "checkpoint-reuse", {
                "agent": role, "stage": stage, "round": round_number,
                "events_replayed": len(events), "reused_at": utcnow(),
            }, canonical=False)
            self.store.update(operation["operation_id"], stage=role,
                              progress={"queries": len(budget.queries), "pages": budget.page_count,
                                        "elapsed_seconds": round(budget.elapsed, 3),
                                        "remaining": budget.remaining()})
            return result
        prior_events = self._prior_attempt_events(operation["operation_id"], role, stage, round_number)
        for event in prior_events:
            budget.observe(event)
        if prior_events:
            self.store.artifact(operation["operation_id"], "retry-usage-replay", {
                "agent": role, "stage": stage, "round": round_number,
                "events_observed": len(prior_events), "replayed_at": utcnow(),
            }, canonical=False)
        manifest = self._manifest(operation, role, round_profile, budget)
        self.store.update(operation["operation_id"], stage=role,
                          progress={"queries": len(budget.queries), "pages": budget.page_count,
                                    "elapsed_seconds": round(budget.elapsed, 3),
                                    "remaining": budget.remaining()})
        self.store.artifact(operation["operation_id"], "manifests", manifest)
        response = self.provider(AgentCall(role, payload, manifest))
        events: list[dict[str, Any]] = []
        result: Any = None
        streamed = not isinstance(response, Mapping)
        raw_provider_result: Any = None
        if isinstance(response, Mapping):
            result = dict(response)
            # Keep a full copy of the provider's original JSON object for audit.
            # Canonical usage events are extracted below, but must not disappear
            # from the preserved raw response.
            raw_provider_result = dict(response)
            events = [dict(event) for event in result.pop("usage_events", []) if isinstance(event, Mapping)]
        else:
            try:
                for event in response:
                    event = dict(event)
                    if event.get("type") == "result":
                        result = event.get("data")
                    else:
                        budget.observe(event); events.append(event)
            except BudgetExceeded:
                cancel = getattr(response, "cancel", None)
                if callable(cancel):
                    cancel()
                self.store.artifact(operation["operation_id"], "raw-agent-events",
                                    {"manifest": manifest, "events": events}, canonical=False)
                raise
        raw = {"manifest": manifest, "events": events,
               "result": raw_provider_result if isinstance(response, Mapping) else result}
        self.store.artifact(operation["operation_id"], "raw-agent-output", raw, canonical=False)
        # Raw output is retained before accounting/validation; invalid provider output
        # remains inspectable but can never be reused as a canonical checkpoint.
        if not streamed:
            for event in events:
                budget.observe(event)
        if role == "retriever":
            candidate_payload = payload.get("candidates", {})
            candidates = candidate_payload.get("candidates", []) if isinstance(candidate_payload, Mapping) else []
            result = _normalize_retriever_passages(result)
            result = _normalize_retriever_identity(result, candidates, operation.get("document_ids", []))
            result_sources = result.get("sources", []) if isinstance(result, Mapping) else []
            events = _retriever_usage_with_ids(events, result_sources)
            # Streamed events were already counted for live budget enforcement;
            # replaying enriched records adds stable aliases without double-counting.
            for event in events:
                budget.observe(event)
        validated = validate_agent_output(role, result)
        # Preserve the established in-process contract (notably locator query
        # receipts) while also storing a dedicated canonical usage-event list.
        if events:
            validated["usage_events"] = events
        self.store.artifact(operation["operation_id"], "agent-results",
                            {"manifest": manifest, "result": validated, "usage_events": events})
        self.store.update(operation["operation_id"],
                          progress={"queries": len(budget.queries), "pages": budget.page_count,
                                    "elapsed_seconds": round(budget.elapsed, 3),
                                    "remaining": budget.remaining()})
        return validated

    def _local_sources(self, operation, queries):
        import documents
        sources={}
        for query in queries:
            for chunk in documents.retrieve(self.store.root.parents[1],operation['case_id'],query,
                    operation['claim_id'],limit=8,document_ids=operation.get('document_ids',[])):
                source_id=chunk['document_id']
                source=sources.setdefault(source_id,{'source_id':source_id,'document_id':source_id,
                    'title':chunk.get('title') or 'PDF local','url':chunk.get('origin_declared') or '',
                    'doi':chunk.get('doi_declared') or '', 'passages':[]})
                if not any(p['evidence_id']==chunk['id'] for p in source['passages']):
                    source['passages'].append({'evidence_id':chunk['id'],'excerpt':chunk['text'],
                        'page':chunk['physical_page'],'location':f"página física {chunk['physical_page']}",
                        'document_sha256':chunk['document_sha256'],'extraction_id':chunk['extraction_id'],
                        'retrieval_method':chunk['retrieval_method']})
        return {'sources':list(sources.values())}

    @staticmethod
    def _enforce_audit(audit: Mapping[str, Any], skeptic: Mapping[str, Any],
                       relevance: Mapping[str, Any], sources: Mapping[str, Any] | None = None,
                       assessments: Mapping[str, Any] | None = None, required_dimensions=None) -> None:
        rows=relevance.get("matrix", [])
        pairs={(row.get("source_id"),row.get("evidence_id")) for row in rows}
        if sources is not None:
            retrieved={(source.get("source_id"),passage.get("evidence_id"))
                       for source in sources.get("sources",[]) for passage in source.get("passages",[])}
            if not pairs.issubset(retrieved):
                raise AgentOutputError("La auditoría semántica referencia pasajes no recuperados.")
        if assessments is not None:
            retrieved_ids={source.get("source_id") for source in (sources or {}).get("sources",[])}
            assessed_ids={row.get("source_id") for row in assessments.get("assessments",[])}
            if assessed_ids!=retrieved_ids:
                raise AgentOutputError("La evaluación de fuentes no corresponde exactamente a las fuentes recuperadas.")
        support_ids=set(skeptic.get("support_source_ids",[]))
        audited_support_ids={row.get("source_id") for row in rows if row.get("overall_relation")=="supports"}
        if not support_ids.issubset(audited_support_ids):
            raise AgentOutputError("Skeptic citó fuentes sin un pasaje auditado como apoyo.")
        if len(pairs)!=len(rows):
            raise AgentOutputError("La matriz contiene pasajes duplicados o sin identidad única.")
        relations={dimension:{row.get("dimensions",{}).get(dimension) for row in rows}
                   for dimension in ("intervention","spacing","comparison","population","material","outcome","horizon")}
        primary_ids={row.get('source_id') for row in (assessments or {}).get('assessments',[])
                     if row.get('primary_status')=='confirmed_primary'}
        required_dimensions=list(required_dimensions or relations)
        if audit.get("decision")=="sufficient_support":
            if skeptic.get("verdict")!="VERIFIED" or not skeptic.get("support_source_ids"):
                raise AgentOutputError("El auditor no puede aprobar respaldo sin veredicto VERIFIED y fuentes de apoyo.")
            missing=[key for key in required_dimensions if not any(row.get('source_id') in primary_ids and
                    row.get('dimensions',{}).get(key)=='supports' for row in rows)]
            if missing:
                raise AgentOutputError("El auditor intentó aprobar dimensiones sin respaldo: "+", ".join(missing))
            if any(row.get('overall_relation')=='contradicts' for row in rows):
                raise AgentOutputError("No se puede cerrar respaldo suficiente mientras quede una contradicción directa en la matriz.")
            if not any(row.get("overall_relation")=="supports" for row in rows):
                raise AgentOutputError("El auditor intentó aprobar sin un pasaje globalmente clasificado como apoyo.")
        if audit.get("decision")=="direct_contradiction":
            if skeptic.get("verdict")!="CONTRADICTED" or not any(row.get("overall_relation")=="contradicts" and row.get('source_id') in primary_ids for row in rows):
                raise AgentOutputError("Una contradicción exige veredicto CONTRADICTED y pasaje contradictorio pertinente.")

    @staticmethod
    def _guard_temporal_wording(sources: Mapping[str, Any], output: Mapping[str, Any]) -> None:
        source_text=" ".join(str(p.get("excerpt", "")) for row in sources.get("sources", [])
                             for p in row.get("passages", [])).casefold()
        rendered=json.dumps(output,ensure_ascii=False).casefold()
        response_time=("four minutes" in source_text and ("allowed" in source_text or "answer" in source_text))
        false_delay=("four minutes after" in rendered or "cuatro minutos después" in rendered)
        if response_time and false_delay:
            raise AgentOutputError("La salida confundió el tiempo para responder con una espera antes de medir.")

    def run(self, operation_id: str) -> dict[str, Any]:
        operation = self.store.load(operation_id)
        if operation["status"] not in ("queued", "failed"):
            raise OperationConflict("La operación ya comenzó o terminó.")
        started = self.clock(); budget = BudgetLedger(started, self.clock)
        operation = self.store.update(operation_id, status="running", stage="planning", error=None)
        operation['_root']=str(self.store.root.parents[1])
        context: dict[str, Any] = {"claim": operation["claim"], "claim_id": operation["claim_id"],
                                   "evidence_mode":operation.get("evidence_mode","question_search"),
                                   "document_ids":operation.get("document_ids",[]),
                                   "input_fingerprint":operation.get("input_fingerprint")}
        try:
            planner = self._call(operation, "planner", context, budget, None)
            formulation = self._call(operation, "formulation_reviewer", {**context, "plan": planner}, budget, None)
            context.update(plan=planner, formulation={**formulation,"claim":operation["claim"],
                                                       "claim_id":operation["claim_id"],"plan":planner,
                                                       "input_fingerprint":operation.get("input_fingerprint")})
            self.store.artifact(operation_id, "search-plan", context)
            receipts, audit, matrices = [], None, []
            for profile in ROUNDS:
                budget.begin_round(profile)
                operation = self.store.update(operation_id, stage=profile["name"], round=profile["number"],
                                              progress={"queries": len(budget.queries), "pages": budget.page_count,
                                                        "elapsed_seconds": round(budget.elapsed, 3),
                                                        "remaining": budget.remaining()})
                try:
                    prior_rows=[row for matrix in matrices for row in matrix.get("matrix",[])]
                    covered={dimension for row in prior_rows for dimension,relation in row.get("dimensions",{}).items()
                             if relation in ("supports","contradicts")}
                    gaps=[dimension for dimension in DIMENSIONS if planner["matrix"].get(dimension) and dimension not in covered]
                    searched_contradictions={query for row in receipts for query in row.get('contradiction_queries',[])}
                    targets=[target for target in planner["retrieval_targets"]
                             if (set(target["dimension_ids"]) & set(gaps)) or
                             (target.get('purpose')=='contradiction' and target.get('query') not in searched_contradictions)]
                    targets=targets[:budget.remaining()['round_queries']]
                    round_context={**context,"round":profile,"gap_dimensions":gaps,
                                   "retrieval_targets":targets,
                                   "contradiction_targets":[target for target in targets if target["purpose"]=="contradiction"]}
                    if operation.get('evidence_mode')=='documents_only':
                        locator={'candidates':[]}
                        retriever=self._local_sources(operation,[target['query'] for target in targets])
                        for source in retriever['sources']:
                            for passage in source['passages']:
                                budget.observe({'type':'page','source_id':source['source_id'],
                                                'body_sha256':passage['evidence_id']})
                    else:
                        locator = self._call(operation, "locator", round_context, budget, profile)
                        retriever = self._call(operation, "retriever", {**round_context, "candidates": locator}, budget, profile)
                        if operation.get('document_ids'):
                            local=self._local_sources(operation,[target['query'] for target in targets])
                            known={source['source_id'] for source in retriever.get('sources',[])}
                            retriever['sources'].extend(source for source in local['sources'] if source['source_id'] not in known)
                    source_eval = self._call(operation, "source_evaluator", {**context, "sources": retriever}, budget, profile)
                    relevance = self._call(operation, "relevance_evaluator", {**context, "sources": retriever,
                                                                               "source_assessments": source_eval}, budget, profile)
                    skeptic = self._call(operation, "skeptic", {**context, "sources": retriever,
                                                                  "source_assessments": source_eval,
                                                                  "support_matrix": relevance}, budget, profile)
                    audit = self._call(operation, "final_auditor", {**context, "sources": retriever,
                                                                      "source_assessments": source_eval,
                                                                      "support_matrix": relevance,
                                                                      "skeptic": skeptic}, budget, profile)
                    required_dimensions=[key for key,value in planner['matrix'].items() if str(value).strip()]
                    self._enforce_audit(audit,skeptic,relevance,retriever,source_eval,required_dimensions)
                    self._guard_temporal_wording(retriever,audit)
                    stopped = "audit:" + audit["decision"]
                    receipt = budget.receipt(profile["number"], stopped)
                    if operation.get('evidence_mode')=='documents_only':
                        searched_targets=targets
                    else:
                        actual_queries={normalize_query(event.get('query','')) for event in locator.get('usage_events',[])
                                        if event.get('type')=='query' and event.get('query')}
                        searched_targets=[target for target in targets if normalize_query(target['query']) in actual_queries]
                    receipt.update(target_dimensions=sorted({dimension for target in searched_targets for dimension in target["dimension_ids"]}),
                                   targeted_queries=[target["query"] for target in searched_targets],
                                   target_purposes=[target['purpose'] for target in searched_targets],
                                   contradiction_queries=[target['query'] for target in searched_targets if target['purpose']=='contradiction'],
                                   sources_considered=len(retriever.get("sources",[])))
                    receipts.append(receipt); self.store.artifact(operation_id, "budget-receipts", receipt)
                    claim_passage_audit={"policy":"claim-passage-audit-v1","claim_id":operation["claim_id"],
                                         "source_assessments":source_eval,"matrix":relevance.get("matrix",[])}
                    self.store.artifact(operation_id, "claim-passage-matrix", claim_passage_audit)
                    self.store.artifact(operation_id, "final-audit", audit)
                    primary_by_id={row.get('source_id'):row.get('primary_status')
                                   for row in source_eval.get('assessments',[])}
                    source_by_id={row.get('source_id'):row for row in retriever.get('sources',[])}
                    matrices.append({**relevance,'matrix':[{**row,'source_status':primary_by_id.get(row.get('source_id')),
                        'source_url':source_by_id.get(row.get('source_id'),{}).get('url'),
                        'source_doi':source_by_id.get(row.get('source_id'),{}).get('doi'),
                        'document_id':source_by_id.get(row.get('source_id'),{}).get('document_id')}
                                                             for row in relevance.get('matrix',[])]})
                    context.update(last_sources=retriever, source_assessments=source_eval,
                                   support_matrix=relevance, skeptic=skeptic, audit=audit,
                                   matrices=matrices, budget_receipts=receipts)
                    required_contradictions={target['query'] for target in planner['retrieval_targets']
                                             if target['purpose']=='contradiction'}
                    completed_contradictions={query for row in receipts for query in row.get('contradiction_queries',[])}
                    if audit["decision"]=="direct_contradiction" or (audit["decision"]=="sufficient_support"
                            and required_contradictions.issubset(completed_contradictions)):
                        break
                except BudgetExceeded as exc:
                    # A provider that tries to exceed its allowance loses only
                    # that partial round. Earlier canonical checkpoints remain
                    # usable and the bounded protocol proceeds.
                    receipt = budget.receipt(profile["number"], "budget_rejected:" + str(exc))
                    receipt.update(target_dimensions=[],targeted_queries=[],target_purposes=[],
                                   contradiction_queries=[],sources_considered=0)
                    receipts.append(receipt)
                    self.store.artifact(operation_id, "budget-receipts", receipt)
                    continue
            exhausted = audit is None or audit["decision"] not in ("sufficient_support", "direct_contradiction")
            bounded = ({"status": "excluded_with_limit", "claim_id": operation["claim_id"],
                        "historical_verdict": "UNSUPPORTED", "rounds_completed": len(receipts),
                        "reason": audit["explanation"] if audit else "Se agotó el protocolo sin una resolución."}
                       if exhausted else None)
            from research_closure import scientific_resolution
            affected=_affected_conclusions(self.store.root.parents[1],operation['case_id'],operation['claim_id'],matrices)
            scientific = scientific_resolution(context["formulation"],matrices,audit or {},
                context.get("skeptic",{}),receipts,evidence_mode=operation.get("evidence_mode","question_search"),
                documents_considered=(operation.get('evidence_mode')=='question_search' or bool(operation.get('document_ids'))),
                affected_conclusions=affected)
            writer = self._call(operation, "writer", {**context, "bounded_resolution": bounded,
                                                        "scientific_resolution":scientific}, budget, None)
            self._guard_temporal_wording(context.get("last_sources",{}),writer)
            result = {"research_summary": writer, "support_matrix":{"matrix":[row for matrix in matrices for row in matrix.get('matrix',[])]},
                      "source_assessments": context.get("source_assessments", {}),
                      "audit": audit, "budget_receipts": receipts,
                      "subquestions": formulation["subquestions"], "bounded_resolution": bounded,
                      "scientific_resolution":scientific,"dimension_matrix":scientific["dimensions"],
                      "outcome": "completed_with_limits" if scientific["resolution"] in ("unresolved","indeterminate") else "resolved",
                      "historical_verdict_changed": False}
            self.store.artifact(operation_id, "result", result)
            return self.store.update(operation_id, status=result["outcome"], stage="complete", result=result,
                                     progress={"queries": len(budget.queries), "pages": budget.page_count,
                                               "elapsed_seconds": round(budget.elapsed, 3),
                                               "remaining": budget.remaining()})
        except (AgentOutputError, BudgetExceeded, KeyError, TypeError, ValueError, OSError) as exc:
            receipt = budget.receipt(self.store.load(operation_id).get("round", 0), "error:" + type(exc).__name__)
            self.store.artifact(operation_id, "budget-receipts", receipt)
            return self.store.update(operation_id, status="failed", stage="failed",
                                     error={"type": type(exc).__name__, "message": str(exc)},
                                     progress={"queries": len(budget.queries), "pages": budget.page_count,
                                               "elapsed_seconds": round(budget.elapsed, 3)})


def start_operation(store: OperationStore, case_id: str, claim_id: str, claim: str) -> dict[str, Any]:
    """Safe integration entrypoint; it only records a queued operation."""
    if not all(isinstance(v, str) and v.strip() for v in (case_id, claim_id, claim)):
        raise ValueError("case_id, claim_id y claim son obligatorios")
    return store.create(case_id.strip(), claim_id.strip(), claim.strip())


def store(root: str | Path) -> OperationStore:
    return OperationStore(Path(root) / ".project-intelligence" / "claim-research")


def get_operation(root: str | Path, operation_id: str) -> dict[str, Any] | None:
    try:
        return store(root).load(operation_id)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def operations_for_claim(root: str | Path, case_id: str, claim_id: str, limit: int = 8) -> list[dict[str, Any]]:
    rows = []
    base = store(root).root
    if not base.exists():
        return rows
    for path in base.glob("*/operation.json"):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if row.get("case_id") == case_id and row.get("claim_id") == claim_id:
            rows.append(row)
    rows.sort(key=lambda row: row.get("updated_at", ""), reverse=True)
    return rows[:limit]


def _affected_conclusions(root: str | Path, case_id: str, current_claim_id: str, matrices) -> list[dict[str, str]]:
    """Flag sibling claims that cite an identity also retrieved in this run; never revise them."""
    try:
        import library
        claims=library.read(library.case_path(case_id)/'claims.json',[])
    except (OSError,ValueError,KeyError):
        return []
    identifiers=set()
    for matrix in matrices:
        for row in matrix.get('matrix',[]):
            if row.get('source_id'):identifiers.add(('source',str(row['source_id']).casefold()))
            if row.get('document_id'):identifiers.add(('document',str(row['document_id']).casefold()))
            if row.get('doi'):identifiers.add(('doi',normalize_doi(str(row['doi']))))
            if row.get('source_doi'):identifiers.add(('doi',normalize_doi(str(row['source_doi']))))
            if row.get('source_url'):identifiers.add(('url',normalize_url(str(row['source_url']))))
    affected=[]
    for claim in claims:
        if claim.get('id')==current_claim_id:continue
        overlaps=[]
        for evidence in claim.get('evidence',[]):
            for key in ('source_id','document_id','doi'):
                value=evidence.get(key)
                kind='document' if key=='document_id' else key
                if value and (kind,str(value).casefold() if kind!='doi' else normalize_doi(str(value))) in identifiers:
                    overlaps.append(kind);break
            url=evidence.get('url')
            if url and ('url',normalize_url(str(url))) in identifiers:overlaps.append('url')
        if overlaps:
            affected.append({'claim_id':claim.get('id',''),'claim':claim.get('claim',''),
                'status':claim.get('status','UNVERIFIED'),
                'reason':'Coincide una identidad de fuente; requiere reevaluación explícita. El veredicto previo no cambió.'})
    return affected


class PipelineProvider:
    """Adapter for one isolated Antigravity process per specialized role."""
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def __call__(self, call: AgentCall) -> dict[str, Any]:
        import pipeline
        skill = self.root / "skills" / ("research-" + call.role.replace("_", "-")) / "SKILL.md"
        if not skill.is_file():
            raise AgentOutputError("Falta la skill del agente: " + call.role)
        remaining = call.manifest.get("budget_remaining", {})
        budget = {
            "timeout_seconds": min(900, max(30, int(remaining.get("seconds", 900)))),
            "max_search_queries": max(0, int(remaining.get("round_queries", 0))),
            "max_pages": max(0, int(remaining.get("round_pages", 0))),
            "max_tool_actions": 80,
        }
        no_tool_roles = {"planner", "formulation_reviewer", "source_evaluator",
                         "relevance_evaluator", "skeptic", "final_auditor", "writer"}
        if call.role in no_tool_roles:
            budget.update(max_tool_actions=0, allowed_tools=[])
        else:
            budget["allowed_tools"] = ["search_web", "read_url_content"]
        stage = "agent_" + call.role
        instructions = skill.read_text(encoding="utf-8")
        if budget["max_search_queries"] == 0:
            instructions += ("\n\nRESTRICCIÓN DEL WRAPPER: quedan 0 consultas. No uses search_web. "
                             "Trabaja sólo con los candidatos, identificadores, URL y contenido recibido.")
        attempts = 2 if call.role in no_tool_roles else 1
        for attempt in range(attempts):
            runner = pipeline.Runner()
            try:
                response = runner.call(stage, instructions,
                                       {"claims": [{"id": call.manifest["claim_ids"][0]}],
                                        "payload": call.payload, "manifest": call.manifest},
                                       agent=call.role, budget=budget)
                break
            except ValueError as exc:
                message = str(exc)
                if "fue detenido por exceder" in message and any(word in message for word in ("consultas", "páginas", "acciones")):
                    raise BudgetExceeded(message) from exc
                lowered = message.casefold()
                transient = ("stream was interrupted" in lowered or
                             (call.role in no_tool_roles and
                              (("respuesta vacía" in lowered and "permisos denegados" in lowered) or
                               "herramienta no permitida" in lowered)))
                if not transient or attempt + 1 >= attempts:
                    raise
        if len(response) != 1 or not isinstance(response[0], dict):
            raise AgentOutputError("El agente debe devolver un array con un único objeto.")
        usage = [];raw_pages=[]
        raw = self.root / ".project-intelligence" / "evidence" / f"{runner.run_id}_{stage}.raw.json"
        try:
            for line in raw.read_text(encoding="utf-8").splitlines():
                event = json.loads(line)
                step = event.get("step_update", {}) if isinstance(event, dict) else {}
                if step.get("step_type") != "tool":
                    continue
                info = step.get("tool_info") or {}; params = info.get("parameters") or {}
                name = step.get("tool_name") or info.get("name")
                if name == "search_web":
                    usage.append({"type": "query", "query": params.get("query") or params.get("Query") or ""})
                elif name == "read_url_content":
                    raw_pages.append({"type": "page", "url": params.get("Url") or params.get("url") or ""})
        except (OSError, ValueError):
            pass
        if call.role=="retriever" and isinstance(response[0].get("sources"),list):
            usage.extend({"type":"page",**{k:row[k] for k in ("url","final_url","doi","source_id","body_sha256") if row.get(k)}}
                         for row in response[0]["sources"])
        else:
            usage.extend(raw_pages)
        return {**response[0], "usage_events": usage}


def _persist_projection(root: Path, operation: Mapping[str, Any]) -> None:
    """Expose the result on the claim without changing its historical verdict."""
    try:
        import library
        folder = library.case_path(operation["case_id"])
        rows = library.read(folder / "claims.json", [])
        for claim in rows:
            if claim.get("id") != operation["claim_id"]:
                continue
            result = operation.get("result") or {}
            claim["research_summary"] = result.get("research_summary")
            claim["support_matrix"] = result.get("support_matrix")
            claim["automatic_next_action"] = ("Consultar la parte no resuelta y sus límites."
                if result.get("bounded_resolution") else "Revisar el resultado automático y sus pasajes.")
            claim["bounded_resolution"] = result.get("bounded_resolution")
            scientific=result.get('scientific_resolution')
            if scientific:
                claim.setdefault('scientific_resolution_history',[]).append(scientific)
                claim['scientific_resolution']=scientific
                claim['dimension_matrix_history']=claim.get('dimension_matrix_history',[])+[
                    {'resolution_id':scientific['resolution_id'],'input_fingerprint':scientific['input_fingerprint'],
                     'dimensions':scientific['dimensions'],'created_at':scientific['created_at']}]
            claim.setdefault("automatic_research_history", []).append({
                "operation_id": operation["operation_id"], "finished_at": operation.get("updated_at"),
                "outcome": result.get("outcome"), "historical_verdict_changed": False,
            })
            library.save(folder / "claims.json", rows)
            break
    except (OSError, ValueError, KeyError):
        return


def run_claim_research(root: str | Path, case_id: str, claim_id: str,
                       operation_id: str | None = None, update=None, progress=None,
                       provider=None, evidence_mode='question_search',document_ids=None,claim_version=None) -> dict[str, Any]:
    """Run the bounded protocol. Called only by an explicit frontend action."""
    root = Path(root); operation_store = store(root)
    try:
        import library
        rows = library.read(library.case_path(case_id) / "claims.json", [])
    except Exception as exc:
        raise ValueError("Expediente inexistente") from exc
    claim = next((row for row in rows if row.get("id") == claim_id), None)
    if not claim:
        raise ValueError("Afirmación inexistente")
    if operation_id:
        operation = operation_store.create_with_id(operation_id, case_id, claim_id, claim["claim"],
            evidence_mode=evidence_mode,document_ids=document_ids,claim_version=claim_version)
        if operation["status"] == "running":
            # An unexpected exception can end the frontend worker after its
            # HTTP operation has been marked failed, leaving the engine
            # projection stale. The HTTP layer only dispatches this function
            # after coalescing active jobs, so a queued retry can safely
            # reclaim the same checkpoints.
            frontend_path = root / ".project-intelligence" / "operations" / (operation_id + ".json")
            try:
                frontend_record = json.loads(frontend_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                frontend_record = {}
            if frontend_record.get("status") == "running" and frontend_record.get("stage") == "Preparando investigación automática":
                operation = operation_store.update(operation_id, status="failed", stage="interrupted",
                    error={"type": "InterruptedWorker", "message": "Se recupera una ejecución interrumpida; se conservan los checkpoints."})
            else:
                raise OperationConflict("La operación ya está en curso.")
    else:
        operation = operation_store.create(case_id,claim_id,claim["claim"],evidence_mode=evidence_mode,
                                            document_ids=document_ids,claim_version=claim_version)
    engine = ResearchOrchestrator(operation_store, provider or PipelineProvider(root))
    finished = engine.run(operation["operation_id"])
    if finished["status"] in ("resolved", "completed_with_limits"):
        _persist_projection(root, finished)
    callback = update or progress
    if callable(callback):
        callback(status="done" if finished["status"] in ("resolved", "completed_with_limits") else "error",
                 stage="Investigación automática terminada", result=finished.get("result"),
                 error=finished.get("error"))
    return finished
