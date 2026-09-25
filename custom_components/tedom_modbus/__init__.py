from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN, CONF_PLUGIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .hub import TedomHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "select", "number", "button"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    name = entry.data["name"]
    host = entry.data["host"]
    port = entry.data["port"]
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    plugin_name = entry.data.get(CONF_PLUGIN)

    # 1. Vytvoření instance Hubu
    hub = TedomHub(hass, name, host, port, scan_interval, plugin_name)

    # 2. Bezpečné načtení pluginu (čekáme, až se načte v executoru)
    await hub.async_init()

    # 3. Společný koordinátor pro všechny platformy
    async def async_update_data():
        return await hass.async_add_executor_job(hub.update)

    hub.coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        name="Tedom",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )
    await hub.coordinator.async_config_entry_first_refresh()

    # 4. Uložení a registrace
    hass.data[DOMAIN][entry.entry_id] = hub
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hub = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(hub.close)
    return unload_ok
