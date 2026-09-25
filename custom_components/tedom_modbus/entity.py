from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class TedomEntity(CoordinatorEntity):
    """Společný základ entit – zařízení, název a unique_id."""

    def __init__(self, hub, entry_id, key, info):
        super().__init__(hub.coordinator)
        self._hub = hub
        self._key = key
        self._info = info
        self._attr_name = f"{hub._name} {info['name']}"
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_icon = info.get("icon")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=hub._name,
            manufacturer="TEDOM",
            model=hub._plugin_name,
        )
