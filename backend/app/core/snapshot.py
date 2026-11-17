"""Deterministic SHA-256 State Snapshot Generator for Optimistic Concurrency Control.

Implements the canonical version-vector hashing algorithm defined in:
docs/07_CANONICAL_STATE_AND_DOMAIN_MODEL.md

Guarantees:
1. Invariance to collection input ordering.
2. Sensitivity to any entity version mutation.
3. Stable canonical JSON serialization (UTF-8, sorted keys, no whitespace).
4. Strictly deterministic output: no dynamic timestamps or volatile metadata.
"""

import hashlib
import json
from typing import Any, Dict, Iterable, List, Sequence, Tuple, Union

SNAPSHOT_SCHEMA_PREFIX: str = "serviceyield-snapshot-v1"


def build_version_vector_from_entities(
    rooftop_version: Tuple[str, int],
    bays: Sequence[Tuple[str, int]],
    technicians: Sequence[Tuple[str, int]],
    repair_orders: Sequence[Tuple[str, int]],
    tasks: Sequence[Tuple[str, int]],
    part_requirements: Sequence[Tuple[str, int]] = (),
    supplier_offers: Sequence[Tuple[str, int]] = (),
) -> List[Tuple[str, str, int]]:
    """Constructs a flattened version vector from entity tuples (entity_id, version).
    
    Returns:
        List of (entity_type, entity_id, version) tuples.
    """
    vector: List[Tuple[str, str, int]] = []
    
    # Rooftop
    vector.append(("rooftop", rooftop_version[0], rooftop_version[1]))
    
    # Bays
    for b_id, b_ver in bays:
        vector.append(("bay", b_id, b_ver))
        
    # Technicians
    for t_id, t_ver in technicians:
        vector.append(("technician", t_id, t_ver))
        
    # Repair Orders
    for ro_id, ro_ver in repair_orders:
        vector.append(("repair_order", ro_id, ro_ver))
        
    # Tasks
    for task_id, task_ver in tasks:
        vector.append(("task", task_id, task_ver))
        
    # Part Requirements
    for p_id, p_ver in part_requirements:
        vector.append(("part_requirement", p_id, p_ver))
        
    # Supplier Offers
    for s_id, s_ver in supplier_offers:
        vector.append(("supplier_offer", s_id, s_ver))
        
    return vector


def compute_snapshot_hash(version_vector: Iterable[Tuple[str, str, int]]) -> str:
    """Computes a deterministic SHA-256 hash from a version vector.
    
    Sorts elements canonically by (entity_type, entity_id), serializes to
    strict JSON with fixed separators, prefixes with the schema version tag,
    and returns the 64-character lowercase hexadecimal digest.
    """
    # Canonical sorting: entity_type ascending, then entity_id ascending
    sorted_vector = sorted(
        [
            {"type": str(item[0]), "id": str(item[1]), "v": int(item[2])}
            for item in version_vector
        ],
        key=lambda x: (x["type"], x["id"]),
    )
    
    payload = {
        "schema": SNAPSHOT_SCHEMA_PREFIX,
        "vector": sorted_vector,
    }
    
    # Canonical JSON string: sorted keys, compact separators, UTF-8 encoded
    canonical_json = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_snapshot_hash_from_dict(snapshot_data: Dict[str, Any]) -> str:
    """Extracts entity versions from a raw dictionary (e.g. from JSON fixture or API payload)
    and computes the deterministic snapshot hash.
    """
    rooftop = snapshot_data.get("rooftop", {})
    rooftop_tuple = (rooftop.get("rooftop_id", "UNKNOWN"), rooftop.get("version", 1))
    
    bays = [(b.get("bay_id"), b.get("version", 1)) for b in snapshot_data.get("bays", [])]
    technicians = [(t.get("tech_id"), t.get("version", 1)) for t in snapshot_data.get("technicians", [])]
    repair_orders = [(r.get("ro_id"), r.get("version", 1)) for r in snapshot_data.get("repair_orders", [])]
    tasks = [(t.get("task_id"), t.get("version", 1)) for t in snapshot_data.get("tasks", [])]
    part_requirements = [(p.get("part_req_id"), p.get("version", 1)) for p in snapshot_data.get("part_requirements", [])]
    supplier_offers = [(s.get("offer_id"), s.get("version", 1)) for s in snapshot_data.get("supplier_offers", [])]
    
    vector = build_version_vector_from_entities(
        rooftop_version=rooftop_tuple,
        bays=bays,
        technicians=technicians,
        repair_orders=repair_orders,
        tasks=tasks,
        part_requirements=part_requirements,
        supplier_offers=supplier_offers,
    )
    return compute_snapshot_hash(vector)


def compute_snapshot_hash_from_models(
    rooftop: Any,
    bays: Sequence[Any],
    technicians: Sequence[Any],
    repair_orders: Sequence[Any],
    tasks: Sequence[Any],
    part_requirements: Sequence[Any] = (),
    supplier_offers: Sequence[Any] = (),
) -> str:
    """Extracts entity versions from SQLAlchemy ORM model instances or Pydantic schemas
    and returns the deterministic snapshot hash.
    """
    rooftop_tuple = (rooftop.rooftop_id, rooftop.version)
    bay_tuples = [(b.bay_id, b.version) for b in bays]
    tech_tuples = [(t.tech_id, t.version) for t in technicians]
    ro_tuples = [(r.ro_id, r.version) for r in repair_orders]
    task_tuples = [(t.task_id, t.version) for t in tasks]
    part_tuples = [(p.part_req_id, p.version) for p in part_requirements]
    offer_tuples = [(s.offer_id, s.version) for s in supplier_offers]
    
    vector = build_version_vector_from_entities(
        rooftop_version=rooftop_tuple,
        bays=bay_tuples,
        technicians=tech_tuples,
        repair_orders=ro_tuples,
        tasks=task_tuples,
        part_requirements=part_tuples,
        supplier_offers=offer_tuples,
    )
    return compute_snapshot_hash(vector)
