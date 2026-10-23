"""Per-charger association validity, independent of physical charging control."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            Association(coordinator, entry, charger)
            for charger in coordinator.brain.config["chargers"]
        ]
    )


class Association(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Association valid"

    def __init__(self, coordinator, entry, charger):
        super().__init__(coordinator)
        self.key = charger["id"]
        self._attr_unique_id = f"{entry.entry_id}_{self.key}_valid"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{self.key}")},
            name=charger["name"],
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def is_on(self):
        return self.coordinator.data[self.key]["valid"]

    @property
    def extra_state_attributes(self):
        return dict(self.coordinator.data[self.key])
