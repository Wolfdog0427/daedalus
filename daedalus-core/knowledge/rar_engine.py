# knowledge/rar_engine.py

"""
Retrieval-Augmented Reasoning (RAR) Engine

The module that turns Daedalus from a knowledge store into a
knowledge engine. Multi-hop graph traversal + evidence gathering +
LLM synthesis = trustworthy, sourced answers.

Architecture fit:
- Uses graph_reasoner.py for path inference and centrality
- Uses retrieval.py for KB search
- Uses trust_scoring.py for confidence weighting
- Uses llm_adapter.py for answer synthesis
- Uses temporal_reasoning.py for time-aware filtering
- Outputs structured ReasoningResult with source attribution
- Governed through integration_layer

Falls back to existing reason_about_claim when RAR components
are unavailable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


# ------------------------------------------------------------
# DATA STRUCTURES
# ------------------------------------------------------------

@dataclass
class EvidenceChain:
    """A chain of evidence linking entities in the knowledge graph."""
    path: List[str]              # entity names in the chain
    relations: List[str]         # relation types along the path
    trust_score: float           # trust-weighted confidence
    source_items: List[str]      # backing KB item IDs
    text_snippets: List[str] = field(default_factory=list)


@dataclass
class ReasoningResult:
    """Complete result of a RAR query."""
    query: str
    answer: str                  # synthesized answer
    confidence: float            # 0-1, trust-weighted
    evidence_chains: List[EvidenceChain] = field(default_factory=list)
    sources_cited: List[str] = field(default_factory=list)
    temporal_context: Optional[Dict[str, Any]] = None
    gaps_detected: List[str] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


# ------------------------------------------------------------
# EVIDENCE GATHERING
# ------------------------------------------------------------

def gather_evidence(
    query: str,
    max_hops: int = 3,
    min_trust: float = 0.3,
    temporal_filter: Optional[float] = None,
) -> List[EvidenceChain]:
    """
    Gather evidence chains from the knowledge graph and KB.

    1. Retrieve relevant items via text search
    2. Extract entities from query
    3. Find graph paths between entities (multi-hop)
    4. Weight each chain by trust scores
    5. Optionally filter by temporal validity
    """
    chains: List[EvidenceChain] = []

    try:
        from knowledge.retrieval import search_knowledge
        from knowledge.trust_scoring import compute_trust_score
        from knowledge.graph_reasoner import infer_relationship, reason_over_graph
        from knowledge.knowledge_graph import get_entity_info
    except ImportError:
        return chains

    search_results = search_knowledge(query, limit=20)
    if not search_results:
        return chains

    if temporal_filter is not None:
        try:
            from knowledge.temporal_reasoning import check_temporal_validity
            search_results = [
                r for r in search_results
                if check_temporal_validity(
                    {"metadata": r.metadata if isinstance(r.metadata, dict) else {}},
                    temporal_filter,
                )
            ]
        except ImportError:
            pass

    graph_analysis = reason_over_graph(query)
    inferred = graph_analysis.get("inferred_relationships", [])

    for rel_wrapper in inferred:
        inference = rel_wrapper.get("inference", {})
        if inference.get("type") == "none":
            continue

        path = inference.get("path", []) or []
        confidence = inference.get("confidence", 0.0)

        if confidence < min_trust:
            continue

        backing_items = []
        snippets = []
        for result in search_results:
            text_lower = result.text.lower()
            if any(entity.lower() in text_lower for entity in path):
                backing_items.append(result.id)
                snippets.append(result.snippet)

        if backing_items:
            relations = inference.get("relations", [])
            chain = EvidenceChain(
                path=path,
                relations=relations if isinstance(relations, list) else [],
                trust_score=confidence,
                source_items=backing_items,
                text_snippets=snippets[:5],
            )
            chains.append(chain)

    for result in search_results[:10]:
        item_dict = {
            "text": result.text,
            "source": result.source,
            "metadata": result.metadata,
        }
        trust = compute_trust_score(item_dict)
        if trust >= min_trust:
            already_cited = any(
                result.id in c.source_items for c in chains
            )
            if not already_cited:
                chains.append(EvidenceChain(
                    path=[],
                    relations=[],
                    trust_score=trust,
                    source_items=[result.id],
                    text_snippets=[result.snippet],
                ))

    chains.sort(key=lambda c: c.trust_score, reverse=True)
    return chains[:15]


# ------------------------------------------------------------
# ANSWER SYNTHESIS
# ------------------------------------------------------------

def synthesize_answer(
    query: str,
    evidence: List[EvidenceChain],
) -> str:
    """
    Combine evidence chains into a coherent answer.
    Uses LLM when available; falls back to structured concatenation.
    """
    if not evidence:
        return "Insufficient evidence to answer this query."

    try:
        from knowledge.llm_adapter import llm_adapter
        if llm_adapter.is_available():
            return _llm_synthesize(query, evidence, llm_adapter)
    except ImportError:
        pass

    return _symbolic_synthesize(query, evidence)


def _llm_synthesize(
    query: str,
    evidence: List[EvidenceChain],
    adapter: Any,
) -> str:
    """Use LLM to synthesize a coherent answer from evidence."""
    evidence_text = ""
    for i, chain in enumerate(evidence[:8]):
        snippets = "; ".join(chain.text_snippets[:3])
        path_str = " -> ".join(chain.path) if chain.path else "direct"
        evidence_text += (
            f"\nEvidence {i+1} (trust: {chain.trust_score:.2f}, "
            f"path: {path_str}):\n{snippets}\n"
        )

    prompt = (
        f"Based on the following evidence from our knowledge base, "
        f"answer this query: {query}\n\n"
        f"{evidence_text}\n\n"
        f"Synthesize a clear, accurate answer. Cite evidence numbers. "
        f"If evidence is insufficient, say so."
    )

    try:
        result = adapter.complete(prompt, max_tokens=512, temperature=0.2)
        if result.strip():
            return result.strip()
    except Exception:
        pass

    return _symbolic_synthesize(query, evidence)


def _symbolic_synthesize(query: str, evidence: List[EvidenceChain]) -> str:
    """Fallback: structured concatenation of evidence."""
    parts = [f"Regarding '{query}':"]

    for i, chain in enumerate(evidence[:5]):
        if chain.path:
            path_str = " -> ".join(chain.path)
            parts.append(
                f"[{i+1}] Path {path_str} "
                f"(confidence: {chain.trust_score:.0%})"
            )
        for snippet in chain.text_snippets[:2]:
            parts.append(f"  - {snippet}")

    return "\n".join(parts)


# ------------------------------------------------------------
# CONFIDENCE ASSESSMENT
# ------------------------------------------------------------

def assess_confidence(evidence: List[EvidenceChain]) -> float:
    """
    Compute overall confidence from evidence chains.
    Weighted by individual trust scores and evidence diversity.
    """
    if not evidence:
        return 0.0

    total_trust = sum(c.trust_score for c in evidence)
    avg_trust = total_trust / len(evidence)

    unique_sources = set()
    for chain in evidence:
        unique_sources.update(chain.source_items)
    diversity_bonus = min(0.2, len(unique_sources) * 0.02)

    graph_chains = sum(1 for c in evidence if c.path)
    graph_bonus = min(0.1, graph_chains * 0.03)

    return min(1.0, avg_trust + diversity_bonus + graph_bonus)


# ------------------------------------------------------------
# GAP DETECTION
# ------------------------------------------------------------

def detect_reasoning_gaps(
    query: str,
    evidence: List[EvidenceChain],
) -> List[str]:
    """
    Identify what's missing to answer the query fully.
    These gaps feed into the active learning module.
    """
    gaps = []

    if not evidence:
        gaps.append(f"No evidence found for: {query}")
        return gaps

    confidence = assess_confidence(evidence)
    if confidence < 0.5:
        gaps.append(f"Low confidence ({confidence:.0%}) for: {query}")

    graph_backed = sum(1 for c in evidence if c.path)
    if graph_backed == 0:
        gaps.append(f"No graph-backed evidence for: {query}")

    try:
        from knowledge.llm_adapter import llm_adapter
        if llm_adapter.is_available():
            snippets = []
            for chain in evidence[:5]:
                snippets.extend(chain.text_snippets[:2])
            context = "\n".join(snippets[:10])

            prompt = (
                f"Given this query: {query}\n"
                f"And this evidence:\n{context[:1000]}\n\n"
                f"What key information is missing to fully answer the query? "
                f"List 1-3 specific knowledge gaps, one per line."
            )
            result = llm_adapter.complete(prompt, max_tokens=128, temperature=0.3)
            for line in result.strip().split("\n"):
                line = line.strip().strip("- ")
                if line and len(line) > 10:
                    gaps.append(line)
    except (ImportError, Exception):
        pass

    return gaps[:5]


# ------------------------------------------------------------
# MAIN RAR PIPELINE
# ------------------------------------------------------------

def reason(
    query: str,
    max_hops: int = 3,
    min_trust: float = 0.3,
    temporal_filter: Optional[float] = None,
) -> ReasoningResult:
    """
    Full RAR pipeline:
    1. Gather evidence chains (graph + retrieval + trust)
    2. Synthesize answer via LLM or symbolic
    3. Assess confidence
    4. Detect knowledge gaps
    """
    start = time.time()
    steps = ["query_received"]

    evidence = gather_evidence(query, max_hops, min_trust, temporal_filter)
    steps.append(f"evidence_gathered:{len(evidence)}_chains")

    answer = synthesize_answer(query, evidence)
    steps.append("answer_synthesized")

    confidence = assess_confidence(evidence)
    steps.append(f"confidence_assessed:{confidence:.2f}")

    gaps = detect_reasoning_gaps(query, evidence)
    if gaps:
        steps.append(f"gaps_detected:{len(gaps)}")

    all_sources = []
    for chain in evidence:
        all_sources.extend(chain.source_items)
    unique_sources = list(dict.fromkeys(all_sources))

    elapsed = (time.time() - start) * 1000

    return ReasoningResult(
        query=query,
        answer=answer,
        confidence=confidence,
        evidence_chains=evidence,
        sources_cited=unique_sources,
        temporal_context={"filter": temporal_filter} if temporal_filter else None,
        gaps_detected=gaps,
        reasoning_steps=steps,
        elapsed_ms=elapsed,
    )


def reason_with_context(
    query: str,
    operator_id: Optional[str] = None,
    timestamp: Optional[float] = None,
) -> ReasoningResult:
    """
    Context-enriched reasoning that incorporates operator preferences
    and temporal awareness.
    """
    temporal_filter = timestamp

    if operator_id:
        try:
            from knowledge.collaborative_memory import get_operator_profile
            profile = get_operator_profile(operator_id)
            prefs = profile.get("preferences", {})
            if prefs.get("temporal_awareness") == "strict":
                temporal_filter = temporal_filter or time.time()
        except ImportError:
            pass

    return reason(query, temporal_filter=temporal_filter)
