from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import TedomEntity

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TedomNumber(hub, entry.entry_id, key, info) for key, info in hub.number_map.items()
    )


class TedomNumber(TedomEntity, NumberEntity):
    def __init__(self, hub, entry_id, key, info):
        super().__init__(hub, entry_id, key, info)
        self._attr_native_unit_of_measurement = info.get("unit")
        self._attr_device_class = info.get("device_class")
        self._attr_native_step = info.get("scale", 1)
        self._attr_mode = NumberMode.BOX

    def _limit(self, which):
        # Limit může být pevné číslo, nebo klíč jiného čteného registru (ComAp "8276*")
        limit = self._info[which]
        if isinstance(limit, str):
            return self._hub.data.get(limit, self._info.get(f"{which}_fallback", 0))
        return limit

    @property
    def native_min_value(self):
        return self._limit("min")

    @property
    def native_max_value(self):
        return self._limit("max")

    @property
    def native_value(self):
        raw_val = self._hub.data.get(self._key)
        if raw_val is None:
            return None
        return round(raw_val, self._info.get("precision", 0))

    async def async_set_native_value(self, value: float) -> None:
        await self.hass.async_add_executor_job(self._hub.write_value, self._info, value)
        # Zapsaná hodnota hned v UI, potvrzení přijde s dalším čtením
        self._hub.data[self._key] = value
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
