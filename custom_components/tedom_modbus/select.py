from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import TedomEntity

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TedomSelect(hub, entry.entry_id, key, info) for key, info in hub.select_map.items()
    )


class TedomSelect(TedomEntity, SelectEntity):
    def __init__(self, hub, entry_id, key, info):
        super().__init__(hub, entry_id, key, info)
        self._attr_options = list(info["value_map"].values())
        self._reverse_map = {v: k for k, v in info["value_map"].items()}

    @property
    def current_option(self):
        raw_val = self._hub.data.get(self._key)
        if raw_val is None:
            return None
        return self._info["value_map"].get(int(raw_val))

    async def async_select_option(self, option: str) -> None:
        await self.hass.async_add_executor_job(
            self._hub.write_value, self._info, self._reverse_map[option]
        )
        await self.coordinator.async_request_refresh()
