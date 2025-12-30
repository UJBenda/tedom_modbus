from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_PLUGIN, CONF_SCAN_INTERVAL
from .hub import TedomHub

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    name = entry.data["name"]
    host = entry.data["host"]
    port = entry.data["port"]
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, 15)
    plugin_name = entry.data.get(CONF_PLUGIN)

    # 1. Vytvoření instance Hubu
    hub = TedomHub(hass, name, host, port, scan_interval, plugin_name)

    # 2. Bezpečné načtení pluginu (čekáme, až se načte v executoru)
    await hub.async_init()

    # 3. Uložení a registrace
    hass.data[DOMAIN][entry.entry_id] = hub
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
