"""UI configuration: explicit devices, source entities and tracker zone states."""

from copy import deepcopy

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import DOMAIN
from .validation import MappingError, validate_config


def entity(domain):
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domain))


def item_schema(kind):
    fields = {
        vol.Required("id"): str,
        vol.Required("name"): str,
        vol.Required("device"): selector.DeviceSelector(),
    }
    if kind == "vehicle":
        fields.update(
            {
                vol.Required("cable"): entity("binary_sensor"),
                vol.Required("tracker"): entity("device_tracker"),
                vol.Optional("fallback_device"): selector.DeviceSelector(),
                vol.Optional("cable_fallback"): entity("binary_sensor"),
                vol.Optional("tracker_fallback"): entity("device_tracker"),
            }
        )
    else:
        fields.update(
            {
                vol.Required("status"): entity("sensor"),
                vol.Required("enabled"): entity("switch"),
                vol.Required("zone_state"): str,
                vol.Optional("override"): entity("input_boolean"),
            }
        )
    return vol.Schema(fields)


class Editor:
    """Shared multi-item editor for config and options flows."""

    config: dict

    async def async_step_menu(self, user_input=None):
        return self.async_show_menu(
            step_id="menu", menu_options=["vehicle", "charger", "remove", "finish"]
        )

    async def async_step_vehicle(self, user_input=None):
        return await self._item("vehicle", "vehicles", user_input)

    async def async_step_charger(self, user_input=None):
        return await self._item("charger", "chargers", user_input)

    async def _item(self, step, group, user_input):
        errors = {}
        if user_input is not None:
            proposed = deepcopy(self.config)
            proposed[group].append(dict(user_input))
            # Validate the complete model as soon as both item types exist.
            try:
                if proposed["vehicles"] and proposed["chargers"]:
                    validate_config(self.hass, proposed)
                elif any(x["id"] == user_input["id"] for x in self.config[group]):
                    raise MappingError("Duplicate ID")
            except MappingError:
                errors["base"] = "invalid_mapping"
            else:
                self.config = proposed
                return await self.async_step_menu()
        return self.async_show_form(
            step_id=step, data_schema=item_schema(step), errors=errors
        )

    async def async_step_remove(self, user_input=None):
        choices = [
            f"{group}:{item['id']}"
            for group in ("vehicles", "chargers")
            for item in self.config[group]
        ]
        if user_input is not None:
            selected = set(user_input.get("items", []))
            for group in ("vehicles", "chargers"):
                self.config[group] = [
                    x
                    for x in self.config[group]
                    if f"{group}:{x['id']}" not in selected
                ]
            return await self.async_step_menu()
        return self.async_show_form(
            step_id="remove",
            data_schema=vol.Schema(
                {
                    vol.Optional("items"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=choices, multiple=True)
                    )
                }
            ),
        )

    async def async_step_finish(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.config["stale_seconds"] = user_input["stale_seconds"]
            try:
                validate_config(self.hass, self.config)
            except MappingError:
                errors["base"] = "invalid_mapping"
            else:
                return self.async_create_entry(
                    title="EV Charger Brain", data=self.config
                )
        return self.async_show_form(
            step_id="finish",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "stale_seconds", default=self.config.get("stale_seconds", 900)
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=86400))
                }
            ),
            errors=errors,
        )


class ConfigFlow(Editor, config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        self.config = {"vehicles": [], "chargers": [], "stale_seconds": 900}
        return await self.async_step_menu()

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlow(config_entry)


class OptionsFlow(Editor, config_entries.OptionsFlow):
    def __init__(self, entry):
        self.config = deepcopy(dict(entry.options or entry.data))

    async def async_step_init(self, user_input=None):
        return await self.async_step_menu()
