# knowledge/federated_exchange.py

"""
Federated Knowledge Exchange

Multiple Daedalus instances can share verified knowledge while each
maintains independent trust scoring and governance. Nothing is
accepted on faith.

Architecture fit:
- Uses source_integrity.py for validation of incoming items
- Uses trust_scoring.py for peer trust management
- Uses version_manager.py for consistency checking
- All imports go through the full verification pipeline
- Peer trust starts at 0.3 (lower than self-ingested)
- First-time peer items quarantined for deeper inspection
- Governed through integration_layer

This module defines the exchange protocol. Actual network transport
is abstracted — peers could be on the same machine, across a LAN,
or over the internet.
"""

from __future__ import annotations

import json
import time
import hmac
import hashlib
import secrets
from typing import Dict, Any, List, Optional
from pathlib import Path

from knowledge._atomic_io import atomic_write_json


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

MIN_EXPORT_TRUST = 0.7
INITIAL_PEER_TRUST = 0.3
PEER_TRUST_INCREMENT = 0.02
PEER_TRUST_DECREMENT = 0.05
QUARANTINE_FIRST_PEER_ITEMS = True


# ------------------------------------------------------------
# STORAGE
# ------------------------------------------------------------

FEDERATED_DIR = Path("data/federated")
PEERS_FILE = FEDERATED_DIR / "peers.json"
EXCHANGE_LOG = FEDERATED_DIR / "exchange_log.jsonl"


def _ensure_storage():
    FEDERATED_DIR.mkdir(parents=True, exist_ok=True)
    if not PEERS_FILE.exists():
        atomic_write_json(PEERS_FILE, {})


# ------------------------------------------------------------
# PEER REGISTRY
# ------------------------------------------------------------

def _load_peers() -> Dict[str, Dict[str, Any]]:
    _ensure_storage()
    try:
        return json.loads(PEERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_peers(peers: Dict[str, Dict[str, Any]]) -> None:
    _ensure_storage()
    atomic_write_json(PEERS_FILE, peers)


def get_peer_registry() -> List[Dict[str, Any]]:
    """List known peers and their trust levels."""
    peers = _load_peers()
    return [
        {
            "peer_id": k,
            "trust": v.get("trust", INITIAL_PEER_TRUST),
            "items_received": v.get("items_received", 0),
            "items_sent": v.get("items_sent", 0),
            "last_sync": v.get("last_sync", 0),
            "first_contact": v.get("first_contact", 0),
        }
        for k, v in peers.items()
    ]


# ------------------------------------------------------------
# PEER KEY MANAGEMENT
# ------------------------------------------------------------

def register_peer(peer_id: str) -> str:
    """Register a new peer and generate a shared secret key.

    Returns the hex-encoded key that must be given to the peer
    out-of-band (operator action).  The key is stored locally.
    """
    peers = _load_peers()
    key = secrets.token_hex(32)
    peers[peer_id] = {
        "trust": INITIAL_PEER_TRUST,
        "first_contact": time.time(),
        "items_received": 0, "items_sent": 0,
        "items_accepted": 0, "items_rejected": 0,
        "last_sync": 0,
        "shared_key": key,
    }
    _save_peers(peers)
    return key


def _get_peer_key(peer_id: str) -> Optional[str]:
    peers = _load_peers()
    peer = peers.get(peer_id)
    if peer is None:
        return None
    return peer.get("shared_key")


def sign_bundle(items: List[Dict[str, Any]], peer_id: str) -> str:
    """Produce an HMAC-SHA256 signature over a JSON-serialised bundle."""
    key = _get_peer_key(peer_id)
    if not key:
        raise ValueError(f"No shared key for peer '{peer_id}'")
    payload = json.dumps(items, sort_keys=True, ensure_ascii=False).encode()
    return hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()


def verify_signature(
    items: List[Dict[str, Any]], peer_id: str, signature: str,
) -> bool:
    """Verify an HMAC-SHA256 signature from a peer."""
    key = _get_peer_key(peer_id)
    if not key:
        return False
    payload = json.dumps(items, sort_keys=True, ensure_ascii=False).encode()
    expected = hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def negotiate_trust(
    peer_id: str,
    peer_stats: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Establish or update trust level with a peer instance.
    Trust starts low and builds through successful exchanges.
    """
    peers = _load_peers()
    peer = peers.get(peer_id)

    if peer is None:
        peer = {
            "trust": INITIAL_PEER_TRUST,
            "first_contact": time.time(),
            "items_received": 0,
            "items_sent": 0,
            "items_accepted": 0,
            "items_rejected": 0,
            "last_sync": 0,
        }
        peers[peer_id] = peer
        _save_peers(peers)
        return INITIAL_PEER_TRUST

    accepted = peer.get("items_accepted", 0)
    rejected = peer.get("items_rejected", 0)
    total = accepted + rejected

    if total > 0:
        success_rate = accepted / total
        trust_adjustment = (success_rate - 0.5) * PEER_TRUST_INCREMENT * total
        peer["trust"] = max(0.1, min(0.9, peer["trust"] + trust_adjustment))

    peers[peer_id] = peer
    _save_peers(peers)
    return peer["trust"]


# ------------------------------------------------------------
# EXPORT
# ------------------------------------------------------------

def export_items(
    filter_query: Optional[str] = None,
    min_trust: float = MIN_EXPORT_TRUST,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Package verified, high-trust items for sharing with peers.
    Only exports items that pass the trust threshold.
    """
    try:
        from knowledge.retrieval import search_knowledge, _iter_items
        from knowledge.trust_scoring import compute_trust_score
    except ImportError:
        return []

    if filter_query:
        results = search_knowledge(filter_query, limit=limit * 2)
        candidates = [
            {"text": r.text, "source": r.source, "metadata": r.metadata,
             "id": r.id, "created_at": r.created_at}
            for r in results
        ]
    else:
        candidates = []
        for item in _iter_items():
            candidates.append(item)
            if len(candidates) >= limit * 3:
                break

    exportable = []
    for item in candidates:
        trust = compute_trust_score(item)
        if trust < min_trust:
            continue

        meta = item.get("metadata", {})
        if isinstance(meta, dict):
            vs = meta.get("verification_status", "")
            if vs not in ("verified", "light_verified"):
                continue

        export_item = {
            "id": item.get("id", ""),
            "text": item.get("text", ""),
            "source": item.get("source", ""),
            "trust_score": trust,
            "content_hash": hashlib.sha256(
                item.get("text", "").encode()
            ).hexdigest()[:16],
            "exported_at": time.time(),
        }
        exportable.append(export_item)

        if len(exportable) >= limit:
            break

    return exportable


# ------------------------------------------------------------
# IMPORT
# ------------------------------------------------------------

def import_items(
    items: List[Dict[str, Any]],
    peer_id: str,
    signature: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate and ingest items from a peer instance.
    Each item goes through the full verification pipeline.
    Peer trust is updated based on acceptance rate.

    When the peer has a shared key, *signature* is mandatory.
    """
    if _get_peer_key(peer_id) is not None:
        if signature is None or not verify_signature(items, peer_id, signature):
            return {
                "action": "federated_import",
                "peer_id": peer_id,
                "error": "signature_invalid_or_missing",
                "total": len(items), "accepted": 0,
                "rejected": len(items), "quarantined": 0,
            }

    peers = _load_peers()
    peer = peers.get(peer_id, {
        "trust": INITIAL_PEER_TRUST,
        "first_contact": time.time(),
        "items_received": 0, "items_sent": 0,
        "items_accepted": 0, "items_rejected": 0,
        "last_sync": 0,
    })

    peer_trust = peer.get("trust", INITIAL_PEER_TRUST)
    is_first_exchange = peer.get("items_received", 0) == 0

    accepted = 0
    rejected = 0
    quarantined = 0

    for item in items:
        text = item.get("text", "")
        source = f"federated:{peer_id}:{item.get('source', 'unknown')}"

        if not text.strip():
            rejected += 1
            continue

        valid = validate_external_provenance(item, peer_id)
        if not valid:
            rejected += 1
            continue

        if QUARANTINE_FIRST_PEER_ITEMS and is_first_exchange:
            try:
                from knowledge.source_integrity import quarantine_item
                quarantine_item(
                    item.get("id", ""), source, text,
                    f"first_peer_exchange:{peer_id}"
                )
                quarantined += 1
                continue
            except ImportError:
                pass

        try:
            from knowledge.batch_ingestion import ingest_batch
            result = ingest_batch(
                items=[{"text": text, "source": source,
                        "metadata": {"peer_id": peer_id,
                                     "peer_trust": peer_trust,
                                     "federated": True}}],
                source=source,
                verification_intensity="deep" if peer_trust < 0.5 else "standard",
            )

            if result.get("ingested", 0) > 0:
                accepted += 1
            else:
                rejected += 1
        except ImportError:
            rejected += 1

    peer["items_received"] = peer.get("items_received", 0) + len(items)
    peer["items_accepted"] = peer.get("items_accepted", 0) + accepted
    peer["items_rejected"] = peer.get("items_rejected", 0) + rejected
    peer["last_sync"] = time.time()
    peers[peer_id] = peer
    _save_peers(peers)

    negotiate_trust(peer_id)

    _log_exchange("import", peer_id, len(items), accepted, rejected, quarantined)

    return {
        "action": "federated_import",
        "peer_id": peer_id,
        "peer_trust": peer.get("trust", INITIAL_PEER_TRUST),
        "total": len(items),
        "accepted": accepted,
        "rejected": rejected,
        "quarantined": quarantined,
    }


# ------------------------------------------------------------
# PROVENANCE VALIDATION
# ------------------------------------------------------------

def validate_external_provenance(
    item: Dict[str, Any],
    peer_id: str,
) -> bool:
    """
    Verify a peer's provenance claims for an item.
    Checks content hash integrity and basic sanity.
    """
    text = item.get("text", "")
    claimed_hash = item.get("content_hash", "")

    actual_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    if not claimed_hash:
        return False
    if actual_hash != claimed_hash:
        return False

    if not text.strip() or len(text) < 10:
        return False

    source = item.get("source", "")
    if "://" in source:
        try:
            from knowledge.source_integrity import validate_url
            url_check = validate_url(source)
            if url_check.get("blocked"):
                return False
        except ImportError:
            pass

    return True


# ------------------------------------------------------------
# SYNC PROTOCOL
# ------------------------------------------------------------

def sync_protocol(
    peer_id: str,
    outgoing_items: Optional[List[Dict[str, Any]]] = None,
    incoming_items: Optional[List[Dict[str, Any]]] = None,
    incoming_signature: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Orchestrate a bidirectional exchange session with a peer.
    """
    result: Dict[str, Any] = {
        "action": "federated_sync",
        "peer_id": peer_id,
        "timestamp": time.time(),
        "export": None,
        "import": None,
    }

    if outgoing_items is not None:
        peers = _load_peers()
        peer = peers.get(peer_id, {})
        peer["items_sent"] = peer.get("items_sent", 0) + len(outgoing_items)
        peers[peer_id] = peer
        _save_peers(peers)

        result["export"] = {
            "items_sent": len(outgoing_items),
        }

    if incoming_items is not None:
        import_result = import_items(incoming_items, peer_id, signature=incoming_signature)
        result["import"] = import_result

    return result


# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------

def _log_exchange(
    direction: str,
    peer_id: str,
    total: int,
    accepted: int,
    rejected: int,
    quarantined: int = 0,
) -> None:
    """Log an exchange event for audit trail."""
    _ensure_storage()
    entry = {
        "direction": direction,
        "peer_id": peer_id,
        "total": total,
        "accepted": accepted,
        "rejected": rejected,
        "quarantined": quarantined,
        "timestamp": time.time(),
    }
    try:
        with EXCHANGE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
