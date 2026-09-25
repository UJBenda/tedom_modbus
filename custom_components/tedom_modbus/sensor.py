from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
import logging

from .const import DOMAIN
from .entity import TedomEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hub = hass.data[DOMAIN][entry.entry_id]

    # Iterujeme přes mapu načteného pluginu
    async_add_entities(
        TedomSensor(hub, entry.entry_id, key, info) for key, info in hub.plugin_map.items()
    )


class TedomSensor(TedomEntity, SensorEntity):
    def __init__(self, hub, entry_id, key, info):
        super().__init__(hub, entry_id, key, info)
        self._attr_native_unit_of_measurement = info.get("unit")
        self._attr_device_class = info.get("device_class")
        self._attr_state_class = info.get("state_class")
        if self._attr_device_class == SensorDeviceClass.ENUM:
            # ENUM senzor musí znát všechny možné stavy předem
            self._attr_options = list(dict.fromkeys(info.get("value_map", {}).values()))

    @property
    def native_value(self):
        """Vrátí hodnotu z Hubu."""
        raw_val = self._hub.data.get(self._key)

        if raw_val is None:
            return None

        # Pokud má senzor mapu hodnot (pro stavy), převedeme číslo na text
        value_map = self._info.get("value_map")
        if value_map:
            state = value_map.get(int(raw_val))
            if state is None:
                _LOGGER.debug(f"Tedom: Neznámý stav {raw_val} pro {self._key}")
            return state

        # Oříznutí desetinných míst
        precision = self._info.get("precision", 0)
        if precision == 0:
            return int(raw_val)
        return round(raw_val, precision)
