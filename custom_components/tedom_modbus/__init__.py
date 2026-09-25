"""Integrace Tedom Modbus - Core pro HA 2026.05 s RPM pojistkou."""
import logging
import asyncio
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST, 
    CONF_PORT, 
    CONF_SCAN_INTERVAL, 
    CONF_NAME, 
    Platform
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.exceptions import ConfigEntryNotReady

from pymodbus.client import AsyncModbusTcpClient
from .pymodbus_compat import DataType, convert_from_registers, ADDR_KW
from .plugin_tedom import TedomPlugin
from .const import (
    DOMAIN, 
    CONF_MODBUS_ADDR, 
    DEFAULT_MODBUS_ADDR,
    CONF_SCAN_INTERVAL_2,
    CONF_SCAN_INTERVAL_3
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.SELECT, Platform.NUMBER]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Nastavení instance integrace a okamžité načtení dat."""
    config = entry.options if entry.options else entry.data
    
    hub = TedomHub(
        hass, 
        config.get(CONF_NAME, "Tedom"), 
        config.get(CONF_HOST), 
        config.get(CONF_PORT, 502), 
        config.get(CONF_SCAN_INTERVAL, 15),
        config.get(CONF_MODBUS_ADDR, DEFAULT_MODBUS_ADDR),
        config.get(CONF_SCAN_INTERVAL_2, 60),
        config.get(CONF_SCAN_INTERVAL_3, 900)
    )
    
    if not await hub.async_connect():
        _LOGGER.warning(f"Tedom ({hub._name}): ComAp je dočasně nedostupný, zkusím to později.")
    else:
        hub._client.close()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"hub": hub}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # OKAMŽITÉ NAČTENÍ: Nečekáme na interval a hned naplníme entity daty
    hass.async_create_task(hub.async_refresh_modbus_data())

    # Registrace pravidelné smyčky
    entry.async_on_unload(
        async_track_time_interval(
            hass, 
            hub.async_refresh_modbus_data, 
            timedelta(seconds=hub.interval_1)
        )
    )
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Odstranění instance integrace."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

class TedomHub:
    """Hub pro komunikaci s Tedomem."""

    def __init__(self, hass, name, host, port, int1, modbus_addr, int2, int3):
        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self.interval_1, self.interval_2, self.interval_3 = int1, int2, int3
        self._modbus_addr = modbus_addr
        
        self.plugin = TedomPlugin()
        self.data = {}
        self.entities = [] 
        self._client = AsyncModbusTcpClient(host=host, port=port, timeout=5)
        self._lock = asyncio.Lock()
        
        self._last_run_2 = 0
        self._last_run_3 = 0

    async def async_connect(self):
        """Připojení s uvolněním slotu."""
        if self._client.connected: return True
        self._client.close() # Synchronní volání (bez await)
        try:
            return await self._client.connect()
        except Exception:
            return False

    async def async_refresh_modbus_data(self, _now=None):
        """Aktualizace dat s ochranou proti zamrzání a RPM pojistkou."""
        if self._lock.locked(): return
        
        async with self._lock:
            if not await self.async_connect(): return

            now = time.time()
            run_2 = (now - self._last_run_2) >= self.interval_2
            run_3 = (now - self._last_run_3) >= self.interval_3

            # Sestavíme seznam všech entit k vyčtení
            to_read = list(self.plugin.SENSOR_TYPES)
            if hasattr(self.plugin, "SELECT_TYPES"): to_read.extend(self.plugin.SELECT_TYPES)
            if hasattr(self.plugin, "NUMBER_TYPES"): to_read.extend(self.plugin.NUMBER_TYPES)

            try:
                for desc in to_read:
                    group = getattr(desc, "interval_group", 1)
                    if (group == 2 and not run_2) or (group == 3 and not run_3): continue

                    try:
                        count = 2 if getattr(desc, "data_type", "") in ["uint32", "int32"] else 1
                        result = await self._client.read_holding_registers(
                            address=desc.address, 
                            count=count, 
                            **{ADDR_KW: self._modbus_addr}
                        )

                        if result and not result.isError():
                            dt = getattr(DataType, getattr(desc, "data_type", "UINT16").upper(), DataType.UINT16)
                            val = convert_from_registers(result.registers, dt)
                            
                            if val is not None:
                                if hasattr(desc, "bitmask") and desc.bitmask is not None:
                                    val = 1 if (int(val) & desc.bitmask) else 0
                                
                                # Uložení (int pro ENUMy/Stavy, float pro zbytek)
                                if getattr(desc, "scale", 1.0) == 1.0:
                                    self.data[desc.key] = int(val)
                                else:
                                    self.data[desc.key] = val * desc.scale
                        
                        await asyncio.sleep(0.08) # Pauza pro stabilitu

                    except Exception as e:
                        _LOGGER.debug(f"Chyba čtení {desc.key}: {e}")

                if run_2: self._last_run_2 = now
                if run_3: self._last_run_3 = now

                # --- VYCHYTÁVKA: RPM POJISTKA ---
                if "rpm" in self.data:
                    # 26: Připraven, 27: Nepřipraven, 37: Havarijní stop, 45: Čekání
                    # Pokud je motor v klidu nebo Modbus hlásí nesmyslných < 505 RPM, vynutíme 0.
                    stavy_klidu = [26, 27, 37, 45, "Připraven", "Nepřipraven", "Havarijní Stop", "Připraven (Waiting)"]
                    if self.data.get("engine_state") in stavy_klidu or self.data["rpm"] < 505:
                        self.data["rpm"] = 0

            finally:
                self._client.close() # Vždy uvolnit TCP slot

            for entity in self.entities:
                if hasattr(entity, "async_write_ha_state"):
                    entity.async_write_ha_state()

    async def async_write_register(self, address, value):
        """Zápis s okamžitým uvolněním slotu."""
        async with self._lock:
            if await self.async_connect():
                try:
                    await self._client.write_register(
                        address=address, value=int(value), **{ADDR_KW: self._modbus_addr}
                    )
                    await asyncio.sleep(0.5)
                    self._hass.async_create_task(self.async_refresh_modbus_data())
                finally:
                    self._client.close()