"""Explicit source ownership validation shared by setup and UI flows."""

import re

from homeassistant.helpers import entity_registry as er


class MappingError(ValueError):
    """A mapping is invalid or ambiguous."""


class SourceNotReady(MappingError):
    """A configured source has not loaded yet."""


def validate_config(hass, config):
    registry = er.async_get(hass)
    if not config.get("vehicles") or not config.get("chargers"):
        raise MappingError("At least one vehicle and charger are required")
    seen_ids, seen_entities = set(), set()
    for kind in ("vehicles", "chargers"):
        for item in config[kind]:
            identity = (kind, item["id"])
            if identity in seen_ids or not re.fullmatch(r"[a-z0-9_]+", item["id"]):
                raise MappingError("IDs must be unique lowercase slugs")
            seen_ids.add(identity)
            if not item.get("name", "").strip():
                raise MappingError("Name required")
            roles = (
                {"status": "sensor", "enabled": "switch", "override": "input_boolean"}
                if kind == "chargers"
                else {
                    "cable": "binary_sensor",
                    "tracker": "device_tracker",
                    "cable_fallback": "binary_sensor",
                    "tracker_fallback": "device_tracker",
                }
            )
            required = (
                ("status", "enabled") if kind == "chargers" else ("cable", "tracker")
            )
            for role in required:
                if not item.get(role):
                    raise MappingError("Required entity missing")
            for role, domain in roles.items():
                entity = item.get(role)
                if not entity:
                    continue
                if entity in seen_entities or not entity.startswith(domain + "."):
                    raise MappingError("Duplicate or wrong-domain source")
                seen_entities.add(entity)
                entry = registry.async_get(entity)
                if hass.states.get(entity) is None:
                    raise SourceNotReady("Configured source entity has not loaded")
                if role == "override":
                    continue
                device = item.get(
                    "fallback_device" if role.endswith("_fallback") else "device"
                )
                if not device or entry is None or entry.device_id != device:
                    raise MappingError(
                        "Source entity does not belong to selected device"
                    )
            if kind == "chargers" and not item.get("zone_state", "").strip():
                raise MappingError("Exact tracker zone state required")
    if not 30 <= config.get("stale_seconds", 900) <= 86400:
        raise MappingError("Freshness must be 30–86400 seconds")
