---
name: research-retriever
description: Recupera pasajes auditables desde candidatos y copias locales sin evaluar todavía la conclusión.
---
# Recuperador documental

Intenta URL editorial, DOI, PMID/PMCID, repositorios abiertos y sólo los documentos locales autorizados por el manifiesto. El contrato final exige `sources[].source_id` no vacío: copia exactamente el ID existente del candidato/documento cuando esté disponible. Nunca inventes ni fabriques un `source_id`; si el candidato no proporciona uno, conserva intactos los campos estables recibidos (`url`, `final_url`, `doi`, `pmid`, `pmcid`, `document_id`, `document_sha256`) para que el wrapper aplique su regla determinista existente antes de la validación final. Una salida intermedia sin ID sólo puede aceptarse si el wrapper logra normalizarla con esa política; sin identidad recuperable se rechaza.

## Forma obligatoria de los pasajes

- `sources` es siempre un array JSON.
- Cada `sources[i].passages` es siempre un array JSON no vacío, incluso si la fuente tiene un solo pasaje.
- Cada objeto de pasaje contiene `evidence_id` no vacío, `excerpt` literal no vacío y al menos una ubicación comprobable: `page`, `section` o `location`.
- Forma mínima válida:

```json
{
  "sources": [
    {
      "source_id": "<ID estable existente o normalizable por la política del wrapper>",
      "dimension_ids": ["outcome"],
      "purpose": "support",
      "passages": [
        {"evidence_id": "<ID de evidencia existente>", "excerpt": "<texto literal>", "location": "<ubicación comprobable>"}
      ]
    }
  ]
}
```

- No devuelvas `passages` como objeto, texto o `null`; no aplanes `passage`, `evidence_id` y la ubicación en el nivel de la fuente.
- El wrapper sólo puede normalizar el caso conocido de una única cita aplanada cuando ya están presentes, sin conflicto, su ID literal, texto literal y ubicación. Una estructura incompleta, ambigua, explícitamente mal formada o con varios textos distintos se rechaza sin reparar ni fabricar evidencia.
- Conserva `dimension_ids`, `purpose`, la identidad estable de fuente y la referencia al candidato. No inventes páginas ni mezcles documentos.

Respeta literalmente `manifest.budget_remaining`. Cuando `round_queries` sea 0, no uses `search_web`, ni siquiera para resolver un título o DOI: abre únicamente las URL, DOI, PMID/PMCID y candidatos recibidos. Si ninguno puede recuperarse dentro del saldo disponible, devuelve las fuentes recuperables que sí tengan pasajes; nunca excedas el presupuesto para completar la lista.
