"""Only anonymous outcome counts leave the integration in diagnostics."""

from collections import Counter

from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "schema_version": 1,
        "operating_mode": "log_only",
        "vehicle_count": len(coordinator.brain.config["vehicles"]),
        "charger_count": len(coordinator.data),
        "modes": dict(Counter(row["mode"] for row in coordinator.data.values())),
    }
