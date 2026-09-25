from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
from .plugin_tedom import TedomPlugin

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    if hasattr(hub.plugin, "NUMBER_TYPES"):
        entities = [TedomNumber(hub, desc) for desc in hub.plugin.NUMBER_TYPES]
        async_add_entities(entities)
        hub.entities.extend(entities)

class TedomNumber(NumberEntity):
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

    @property
    def native_value(self):
        return self._hub.data.get(self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        write_val = int(value / self.entity_description.scale)
        await self._hub.async_write_register(self.entity_description.address, write_val)
        self._hub.data[self.entity_description.key] = value