from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .plugin_tedom import TedomPlugin

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    if hasattr(hub.plugin, "BUTTON_TYPES"):
        entities = [TedomButton(hub, desc) for desc in hub.plugin.BUTTON_TYPES]
        async_add_entities(entities)

class TedomButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, hub, description):
        self._hub = hub
        self.entity_description = description
        self._attr_unique_id = f"{hub._name}_{description.key}".lower()
        self._attr_name = description.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._hub._name)},
            name=self._hub._name,
            manufacturer="Tedom",
            model=TedomPlugin.NAME,
        )

    async def async_press(self) -> None:
        desc = self.entity_description
        if desc.command is not None:
            # ComAp příkaz (Start/Stop) přes příkazové registry 46359-46361
            await self._hub.async_send_command(desc.command, desc.command_return)
        else:
            await self._hub.async_write_register(address=desc.address, value=desc.payload)
