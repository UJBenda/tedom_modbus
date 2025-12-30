from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.components.sensor import SensorEntity
from datetime import timedelta
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hub = hass.data[DOMAIN][entry.entry_id]
    
    # Koordinátor pro pravidelné čtení
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Tedom Sensor",
        update_method=lambda: hass.async_add_executor_job(hub.update),
        update_interval=timedelta(seconds=hub._scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    entities = []
    # Iterujeme přes mapu načteného pluginu
    for key, info in hub.plugin_map.items():
        entities.append(TedomSensor(coordinator, hub, key, info))

    async_add_entities(entities)


class TedomSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, hub, key, info):
        super().__init__(coordinator)
        self._hub = hub
        self._key = key
        self._info = info
        self._attr_name = f"{hub._name} {info['name']}"
        self._attr_unique_id = f"{hub._name}_{key}".lower().replace(" ", "_")
        self._attr_native_unit_of_measurement = info.get("unit")
        self._attr_device_class = info.get("device_class")
        self._attr_state_class = info.get("state_class")
        self._attr_icon = info.get("icon")

    @property
    def native_value(self):
        """Vrátí hodnotu z Hubu."""
        raw_val = self._hub.data.get(self._key)
        
        if raw_val is None:
            return None

        # Pokud má senzor mapu hodnot (pro stavy), převedeme číslo na text
        value_map = self._info.get("value_map")
        if value_map:
            return value_map.get(int(raw_val), raw_val)
        
        # Oříznutí desetinných míst
        precision = self._info.get("precision", 0)
        if precision == 0:
            return int(raw_val)
        return round(raw_val, precision)
