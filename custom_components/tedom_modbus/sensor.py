from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_info import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from datetime import timedelta
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hub = hass.data[DOMAIN][entry.entry_id]

    async def async_update_data():
        return await hass.async_add_executor_job(hub.update)

    # Koordinátor pro pravidelné čtení
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        name="Tedom Sensor",
        update_method=async_update_data,
        update_interval=timedelta(seconds=hub._scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=hub._name,
        manufacturer="TEDOM",
        model=hub._plugin_name,
    )

    # Iterujeme přes mapu načteného pluginu
    async_add_entities(
        TedomSensor(coordinator, hub, entry.entry_id, device_info, key, info)
        for key, info in hub.plugin_map.items()
    )


class TedomSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, hub, entry_id, device_info, key, info):
        super().__init__(coordinator)
        self._hub = hub
        self._key = key
        self._info = info
        self._attr_name = f"{hub._name} {info['name']}"
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = device_info
        self._attr_native_unit_of_measurement = info.get("unit")
        self._attr_device_class = info.get("device_class")
        self._attr_state_class = info.get("state_class")
        self._attr_icon = info.get("icon")
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
