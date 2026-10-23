from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import CoreState
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from test_engine import NOW, states

from custom_components.ev_charger_brain.const import DOMAIN
from custom_components.ev_charger_brain.engine import Brain, Reading


async def test_missing_source_retries_setup(hass, sources):
    hass.states.async_remove("sensor.one")
    entry = MockConfigEntry(domain=DOMAIN, data=sources)
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_invalid_device_is_actionable_setup_error(hass, sources):
    sources["chargers"][0]["device"] = "wrong"
    entry = MockConfigEntry(domain=DOMAIN, data=sources)
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == ConfigEntryState.SETUP_ERROR


async def test_event_update_and_watchdog_expiry(hass, sources, freezer):
    hass.set_state(CoreState.running)
    entry = MockConfigEntry(domain=DOMAIN, data=sources)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    with patch("homeassistant.core.ServiceRegistry.async_call") as calls:
        hass.states.async_set("sensor.one", "disconnected")
        await hass.async_block_till_done()
        assert hass.states.get("sensor.ev_charger_assignments").state == "1"
        freezer.move_to(dt_util.utcnow() + timedelta(seconds=916))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert hass.states.get("sensor.ev_charger_assignments").state == "0"
        calls.assert_not_called()
    assert await hass.config_entries.async_unload(entry.entry_id)


def test_stale_primary_uses_fresh_fallback(config):
    config["vehicles"][0]["cable_fallback"] = "binary_sensor.fallback"
    data = states()
    data["binary_sensor.a"] = Reading("off", NOW - timedelta(seconds=901))
    data["binary_sensor.fallback"] = Reading("on", NOW)
    assert Brain(config).evaluate(data, NOW)["one"]["car"] == "a"


def test_unavailable_charger_reserves_previous_vehicle(config):
    config["chargers"][1]["zone_state"] = "home"
    brain = Brain(config)
    brain.evaluate(states(**{"sensor.two": "disconnected"}), NOW)
    rows = brain.evaluate(states(**{"sensor.one": "unavailable"}), NOW)
    assert not any(row["valid"] for row in rows.values())
    assert rows["two"]["car"] is None


def test_order_independent_graph(config):
    config["chargers"][1]["zone_state"] = "home"
    reversed_config = deepcopy(config)
    reversed_config["chargers"].reverse()
    assert Brain(config).evaluate(states(), NOW) == Brain(reversed_config).evaluate(
        states(), NOW
    )
