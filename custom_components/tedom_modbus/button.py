from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import TedomEntity

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TedomButton(hub, entry.entry_id, key, info) for key, info in hub.button_map.items()
    )


class TedomButton(TedomEntity, ButtonEntity):
    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(
            self._hub.send_command, self._info["argument"], self._info["expected_return"]
        )
        await self.coordinator.async_request_refresh()
