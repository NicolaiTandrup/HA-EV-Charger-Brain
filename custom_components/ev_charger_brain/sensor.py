"""Versioned aggregate association interface."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


async def async_setup_entry(hass, entry, async_add_entities):
    from .const import DOMAIN

    async_add_entities([Assignments(hass.data[DOMAIN][entry.entry_id], entry)])


class Assignments(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "EV charger assignments"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_assignments"

    @property
    def native_value(self):
        return sum(row["valid"] for row in self.coordinator.data.values())

    @property
    def extra_state_attributes(self):
        return {
            "schema_version": 1,
            "operating_mode": "log_only",
            "updated_at": self.coordinator.updated_at.isoformat(),
            "assignments": [
                dict(row) for row in self.coordinator.data.values() if row["valid"]
            ],
            "chargers": [dict(row) for row in self.coordinator.data.values()],
        }
