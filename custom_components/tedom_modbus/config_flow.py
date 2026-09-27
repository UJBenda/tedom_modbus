import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import (
    DOMAIN, DEFAULT_PORT, DEFAULT_NAME, CONF_MODBUS_ADDR, DEFAULT_MODBUS_ADDR,
    DEFAULT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_2, DEFAULT_SCAN_INTERVAL_3,
    CONF_SCAN_INTERVAL_2, CONF_SCAN_INTERVAL_3,
    CONF_GEN_TYPE, GEN_TYPES, GEN_TYPE_ASYNC,
    CONF_PRICE_ENTITY, CONF_TANK_TEMP_ENTITY, DEFAULT_PRICE_ENTITY,
)

# Výběr senzoru ceny jen z integrace Czech Energy Spot Prices, teploty jen z teplotních senzorů
_PRICE_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor", integration="cz_energy_spot_prices")
)
_TEMP_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
)

class TedomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input.get(CONF_NAME, DEFAULT_NAME), data=user_input)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Required(CONF_MODBUS_ADDR, default=DEFAULT_MODBUS_ADDR): int,
            vol.Required(CONF_GEN_TYPE, default=GEN_TYPE_ASYNC): vol.In(GEN_TYPES),
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            vol.Optional(CONF_PRICE_ENTITY, default=DEFAULT_PRICE_ENTITY): _PRICE_SELECTOR,
            vol.Optional(CONF_TANK_TEMP_ENTITY): _TEMP_SELECTOR,
        }))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TedomOptionsFlowHandler()

class TedomOptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        
        conf = self.config_entry.data
        opts = self.config_entry.options
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required(CONF_HOST, default=opts.get(CONF_HOST, conf.get(CONF_HOST, ""))): str,
            vol.Required(CONF_PORT, default=opts.get(CONF_PORT, conf.get(CONF_PORT, DEFAULT_PORT))): int,
            vol.Required(CONF_MODBUS_ADDR, default=opts.get(CONF_MODBUS_ADDR, conf.get(CONF_MODBUS_ADDR, DEFAULT_MODBUS_ADDR))): int,
            vol.Required(CONF_GEN_TYPE, default=opts.get(CONF_GEN_TYPE, conf.get(CONF_GEN_TYPE, GEN_TYPE_ASYNC))): vol.In(GEN_TYPES),
            vol.Optional(CONF_SCAN_INTERVAL, default=opts.get(CONF_SCAN_INTERVAL, conf.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))): int,
            # Plánovač podle spotových cen
            vol.Optional(CONF_PRICE_ENTITY, default=opts.get(CONF_PRICE_ENTITY, conf.get(CONF_PRICE_ENTITY, DEFAULT_PRICE_ENTITY))): _PRICE_SELECTOR,
            vol.Optional(CONF_TANK_TEMP_ENTITY, description={"suggested_value": opts.get(CONF_TANK_TEMP_ENTITY, conf.get(CONF_TANK_TEMP_ENTITY))}): _TEMP_SELECTOR,
        }))