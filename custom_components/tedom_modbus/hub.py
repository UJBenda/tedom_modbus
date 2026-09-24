import logging
import importlib
import inspect
from pymodbus.client import ModbusTcpClient
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)

# pymodbus 3.10+ přejmenoval parametr "slave" na "device_id"
_UNIT_KWARG = (
    "device_id"
    if "device_id" in inspect.signature(ModbusTcpClient.read_holding_registers).parameters
    else "slave"
)

class TedomHub:
    def __init__(self, hass: HomeAssistant, name, host, port, scan_interval, plugin_name):
        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self._client = ModbusTcpClient(host=host, port=port)
        self._scan_interval = scan_interval
        self._plugin_name = plugin_name
        self.plugin_map = {}
        self.register_base = 0
        self.data = {}

    async def async_init(self):
        """Asynchronní inicializace - bezpečné načtení pluginu."""
        def load_plugin():
            try:
                module = importlib.import_module(f".{self._plugin_name}", __package__)
                return module.PLUGIN_MAP, getattr(module, "REGISTER_BASE", 0)
            except ImportError as e:
                _LOGGER.error(f"Tedom: Nelze načíst plugin '{self._plugin_name}'. Chyba: {e}")
            except Exception as e:
                _LOGGER.error(f"Tedom: Chyba v pluginu '{self._plugin_name}': {e}")
            return {}, 0

        # Spustíme import v "executoru", aby neblokoval smyčku HA
        self.plugin_map, self.register_base = await self._hass.async_add_executor_job(load_plugin)

        if self.plugin_map:
            _LOGGER.info(f"Tedom: Úspěšně načten plugin {self._plugin_name} s {len(self.plugin_map)} registry.")

    def update(self):
        """Hlavní smyčka čtení dat (běží v executoru)."""
        if not self.plugin_map:
            return self.data

        if not self._client.connect():
            self.data = {}
            raise UpdateFailed(f"Tedom: Nelze se připojit k {self._host}:{self._port}")

        data = {}
        try:
            for key, info in self.plugin_map.items():
                data_type = getattr(
                    self._client.DATATYPE, info.get("register_type", "int16").upper()
                )
                address = info["register"] - self.register_base if "register" in info else info["address"]
                try:
                    # Comap používá Holding registry
                    result = self._client.read_holding_registers(
                        address, count=data_type.value[1], **{_UNIT_KWARG: 1}
                    )
                    if result.isError():
                        _LOGGER.debug(f"Tedom: Chyba čtení {key}: {result}")
                        continue

                    val = self._client.convert_from_registers(result.registers, data_type=data_type)

                    # Aplikace měřítka
                    data[key] = val * info.get("scale", 1)
                except Exception as e:
                    _LOGGER.debug(f"Tedom: Chyba čtení {key}: {e}")
        finally:
            self._client.close()

        self.data = data
        return data

    def close(self):
        self._client.close()
