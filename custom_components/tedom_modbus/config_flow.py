import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PLUGIN,
    CONF_PLUGIN,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_UNIT_ID,
    AVAILABLE_PLUGINS,
)

class TedomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Zabráníme přidání stejné jednotky dvakrát
            await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(int, vol.Range(min=1, max=65535)),
                vol.Required(CONF_PLUGIN, default=DEFAULT_PLUGIN): vol.In(AVAILABLE_PLUGINS),
                vol.Optional(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(int, vol.Range(min=1, max=247)),
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(int, vol.Range(min=5)),
            })
        )
