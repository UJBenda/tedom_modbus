import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME, CONF_SCAN_INTERVAL
from .const import DOMAIN, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_NAME, CONF_PLUGIN, AVAILABLE_PLUGINS

class TedomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        # Vyrobíme seznam pro dropdown menu (Klíč: Popis)
        plugin_options = {k: v for k, v in AVAILABLE_PLUGINS.items()}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_PLUGIN, default="tedom_intelicompact"): vol.In(plugin_options),
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            })
        )
