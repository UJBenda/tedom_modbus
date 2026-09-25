from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
from .plugin_tedom import TedomPlugin

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    if hasattr(hub.plugin, "SENSOR_TYPES"):
        entities = [TedomSensor(hub, desc) for desc in hub.plugin.SENSOR_TYPES]
        async_add_entities(entities)
        hub.entities.extend(entities)

class TedomSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, hub, description):
        self._hub = hub
        self.entity_description = description
        self._attr_unique_id = f"{hub._name}_{description.key}".lower()
        self._attr_name = description.name
        self._attr_should_poll = False
        

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
        val = self._hub.data.get(self.entity_description.key)
        if val is None: return None
        if self.entity_description.value_map:
            return self.entity_description.value_map.get(int(val), str(val))
        return val