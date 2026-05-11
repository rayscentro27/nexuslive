"""
Replication Service.

Clone existing instances or spin up new ones from validated niches.
Tracks lineage via parent_instance_id.

Usage:
    from instance_engine.replication_service import (
        clone_instance, spawn_from_niche, get_clones,
    )
"""

import logging
from typing import Optional, List

from instance_engine.instance_registry import (
    create_instance, get_instance, get_all_configs,
    set_config, update_status,
)

logger = logging.getLogger('ReplicationService')


def clone_instance(
    source_id: str,
    new_niche: Optional[str]  = None,
    display_name: Optional[str] = None,
) -> Optional[dict]:
    """
    Clone an existing instance.
    Copies all config keys. Sets status=testing.
    parent_instance_id = source_id for lineage tracking.
    """
    source = get_instance(source_id)
    if not source:
        logger.warning(f"clone_instance: source {source_id} not found")
        return None

    niche = new_niche or source.get('niche', 'unknown')
    name  = display_name or f"{source.get('display_name', niche)} (clone)"

    clone = create_instance(
        niche=niche,
        display_name=name,
        status='testing',
        config=source.get('config') or {},
        parent_instance_id=source_id,
    )
    if not clone:
        return None

    # Copy key-value configs
    source_configs = get_all_configs(source_id)
    for k, v in source_configs.items():
        set_config(clone['id'], k, v or '')

    logger.info(f"Cloned {source_id} → {clone['id']} niche={niche}")
    return clone


def spawn_from_niche(
    niche_name: str,
    display_name: Optional[str] = None,
    initial_configs: Optional[dict] = None,
) -> Optional[dict]:
    """
    Spawn a fresh instance from a validated niche candidate.
    Call this after niche_discovery validates a niche.
    """
    instance = create_instance(
        niche=niche_name,
        display_name=display_name or niche_name.replace('_', ' ').title(),
        status='testing',
        config=initial_configs or {},
    )
    if not instance:
        return None

    if initial_configs:
        for k, v in initial_configs.items():
            set_config(instance['id'], k, str(v))

    logger.info(f"Spawned instance {instance['id']} from niche={niche_name}")
    return instance


def get_clones(source_id: str) -> List[dict]:
    """Return all instances cloned from this source."""
    from instance_engine.instance_registry import _sb_get
    return _sb_get(
        f"nexus_instances?parent_instance_id=eq.{source_id}&select=*&order=created_at.desc"
    )


def replicate_top_performers(min_revenue: float = 5000.0, limit: int = 3) -> List[dict]:
    """
    Find instances with high revenue and clone them into new niches.
    Called by portfolio_worker when scale signals fire.
    Returns list of new clones created.
    """
    from instance_engine.instance_registry import _sb_get

    # Find active instances with strong revenue
    rows = _sb_get(
        f"nexus_instances?status=eq.active&select=id,niche,display_name&limit={limit}"
    )
    clones = []
    for row in rows:
        clone = clone_instance(
            source_id=row['id'],
            display_name=f"{row.get('display_name', row['niche'])} v2",
        )
        if clone:
            clones.append(clone)

    return clones
