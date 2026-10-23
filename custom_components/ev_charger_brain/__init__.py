"""Read-only EV Charger Brain integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .coordinator import BrainCoordinator
from .validation import MappingError, SourceNotReady, validate_config


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = entry.options or entry.data
    try:
        validate_config(hass, config)
    except SourceNotReady as err:
        raise ConfigEntryNotReady(str(err)) from err
    except MappingError as err:
        raise ConfigEntryError(str(err)) from err
    coordinator = BrainCoordinator(hass, entry, config)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    coordinator.listen(entry)
    entry.async_on_unload(entry.add_update_listener(_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False
