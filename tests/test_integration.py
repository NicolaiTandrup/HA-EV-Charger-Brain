from copy import deepcopy
from unittest.mock import patch

import pytest
from homeassistant.core import CoreState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ev_charger_brain.const import DOMAIN
from custom_components.ev_charger_brain.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.ev_charger_brain.validation import MappingError, validate_config


async def test_setup_events_diagnostics_unload_no_services(hass, sources):
    hass.set_state(CoreState.running)
    entry = MockConfigEntry(domain=DOMAIN, data=sources, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    with patch("homeassistant.core.ServiceRegistry.async_call") as calls:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        aggregate = hass.states.get("sensor.ev_charger_assignments")
        assert aggregate.state == "2"
        assert aggregate.attributes["schema_version"] == 1
        assert len(aggregate.attributes["assignments"]) == 2
        assert (
            hass.states.get("binary_sensor.charger_one_association_valid").state == "on"
        )
        coordinator = hass.data[DOMAIN][entry.entry_id]
        hass.states.async_set("sensor.one", "disconnected")
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get("sensor.ev_charger_assignments").state == "1"
        assert (
            hass.states.get("binary_sensor.charger_one_association_valid").state
            == "off"
        )
        diagnostics = await async_get_config_entry_diagnostics(hass, entry)
        assert diagnostics["charger_count"] == 2
        assert "sensor.one" not in str(diagnostics) and "Vehicle A" not in str(
            diagnostics
        )
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert entry.entry_id not in hass.data[DOMAIN]
        calls.assert_not_called()


async def test_reject_wrong_device_duplicate_and_domain(hass, sources):
    validate_config(hass, sources)
    for mutation in ("wrong_device", "duplicate", "wrong_domain"):
        bad = deepcopy(sources)
        if mutation == "wrong_device":
            bad["chargers"][0]["device"] = bad["vehicles"][0]["device"]
        elif mutation == "duplicate":
            bad["chargers"][1]["status"] = bad["chargers"][0]["status"]
        else:
            bad["chargers"][0]["enabled"] = "sensor.one"
        with pytest.raises(MappingError):
            validate_config(hass, bad)


async def test_full_config_and_options_flow(hass, sources):
    from homeassistant.data_entry_flow import FlowResultType

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.MENU
    for step, group in (("vehicle", "vehicles"), ("charger", "chargers")):
        for item in sources[group]:
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {"next_step_id": step}
            )
            assert result["type"] == FlowResultType.FORM
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], item
            )
            assert result["type"] == FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    with patch(
        "custom_components.ev_charger_brain.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"stale_seconds": 600}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
    entry = result["result"]
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"stale_seconds": 800}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["stale_seconds"] == 800
