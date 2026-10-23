import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def config():
    return {
        "vehicles": [
            {
                "id": "a",
                "name": "Vehicle A",
                "device": "va",
                "cable": "binary_sensor.a",
                "tracker": "device_tracker.a",
            },
            {
                "id": "b",
                "name": "Vehicle B",
                "device": "vb",
                "cable": "binary_sensor.b",
                "tracker": "device_tracker.b",
            },
        ],
        "chargers": [
            {
                "id": "one",
                "name": "Charger One",
                "device": "c1",
                "status": "sensor.one",
                "enabled": "switch.one",
                "zone_state": "home",
                "override": "input_boolean.manual",
            },
            {
                "id": "two",
                "name": "Charger Two",
                "device": "c2",
                "status": "sensor.two",
                "enabled": "switch.two",
                "zone_state": "work",
            },
        ],
        "stale_seconds": 900,
    }


@pytest.fixture
async def sources(hass, config):
    devices, entities = dr.async_get(hass), er.async_get(hass)
    source_entry = MockConfigEntry(domain="demo")
    source_entry.add_to_hass(hass)
    for group in ("vehicles", "chargers"):
        for item in config[group]:
            device = devices.async_get_or_create(
                config_entry_id=source_entry.entry_id,
                identifiers={("demo", item["device"])},
            )
            item["device"] = device.id
            for role in ("cable", "tracker", "status", "enabled"):
                if role not in item:
                    continue
                entity_id = item[role]
                domain, obj = entity_id.split(".")
                entities.async_get_or_create(
                    domain, "demo", obj, suggested_object_id=obj, device_id=device.id
                )
                value = {
                    "cable": "on",
                    "tracker": "home" if item["id"] == "a" else "work",
                    "status": "charging",
                    "enabled": "off",
                }[role]
                hass.states.async_set(entity_id, value)
    hass.states.async_set("input_boolean.manual", "off")
    return config
