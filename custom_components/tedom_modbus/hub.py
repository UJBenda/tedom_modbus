import logging
import importlib
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class TedomHub:
    def __init__(self, hass: HomeAssistant, name, host, port, scan_interval, plugin_name):
        self._hass = hass
        self._name = name
        self._client = ModbusTcpClient(host=host, port=port)
        self._scan_interval = scan_interval
        self._plugin_name = plugin_name
        self.plugin_map = {}
        self.data = {}

    async def async_init(self):
        """Asynchronní inicializace - bezpečné načtení pluginu."""
        def load_plugin():
            try:
                # Absolutní import je bezpečnější
                full_module_name = f"custom_components.tedom_modbus.{self._plugin_name}"
                module = importlib.import_module(full_module_name)
                return module.PLUGIN_MAP
            except ImportError as e:
                _LOGGER.error(f"Tedom: Nelze načíst plugin '{self._plugin_name}'. Chyba: {e}")
                return {}
            except Exception as e:
                _LOGGER.error(f"Tedom: Chyba v pluginu '{self._plugin_name}': {e}")
                return {}

        # Spustíme import v "executoru", aby neblokoval smyčku HA
        self.plugin_map = await self._hass.async_add_executor_job(load_plugin)
        
        if self.plugin_map:
            _LOGGER.info(f"Tedom: Úspěšně načten plugin {self._plugin_name} s {len(self.plugin_map)} registry.")

    def update(self):
        """Hlavní smyčka čtení dat."""
        if not self.plugin_map:
            return

        # Připojení (blokující operace, ale v update_coordinatoru běží v threadu, takže OK)
        if not self._client.connect():
            _LOGGER.warning(f"Tedom: Nelze se připojit k {self._client.comm_params.host}")
            return

        for key, info in self.plugin_map.items():
            address = info["address"]
            count = 2 if info.get("register_type") == "uint32" else 1
            
            try:
                # Comap používá Holding registry
                result = self._client.read_holding_registers(address, count=count, slave=1)
                
                if result.isError():
                    continue

                decoder = BinaryPayloadDecoder.fromRegisters(
                    result.registers, byteorder=Endian.Big, wordorder=Endian.Big
                )

                if info.get("register_type") == "uint32":
                    val = decoder.decode_32bit_uint()
                else:
                    val = decoder.decode_16bit_int()

                # Aplikace měřítka
                val = val * info.get("scale", 1)
                self.data[key] = val

            except Exception as e:
                _LOGGER.debug(f"Chyba čtení {key}: {e}")
        
        self._client.close()
