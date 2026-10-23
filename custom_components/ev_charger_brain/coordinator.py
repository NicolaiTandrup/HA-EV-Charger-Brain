"""Event-driven local state ingestion with a freshness watchdog."""

import logging
from datetime import timedelta

from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .engine import Brain, Reading

_LOGGER = logging.getLogger(__name__)


class BrainCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, config):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=15),
        )
        self.brain = Brain(config)
        self.sources = {
            v
            for group in ("chargers", "vehicles")
            for item in config[group]
            for k, v in item.items()
            if k
            in {
                "status",
                "enabled",
                "override",
                "cable",
                "tracker",
                "cable_fallback",
                "tracker_fallback",
            }
            and v
        }
        self.updated_at = None

    def listen(self, entry):
        entry.async_on_unload(
            async_track_state_change_event(self.hass, self.sources, self._changed)
        )

    async def _changed(self, event):
        await self.async_request_refresh()

    async def _async_update_data(self):
        states = {}
        for entity in self.sources:
            state = self.hass.states.get(entity)
            if state:
                states[entity] = Reading(state.state, state.last_reported)
        self.updated_at = dt_util.utcnow()
        return self.brain.evaluate(states, self.updated_at)
