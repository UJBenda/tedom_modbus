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
        self.data = {}
        
        # Dynamický import pluginu podle jména
        # Hledá soubor ve stejné složce: custom_components.tedom_modbus.plugin_XY
        try:
            module = importlib.import_module(f".plugin_{plugin_name}", package="custom_components.tedom_modbus")
            self.plugin_map = module.PLUGIN_MAP
            _LOGGER.info(f"Načten plugin: {plugin_name}")
        except ImportError as e:
            _LOGGER.error(f"Nelze načíst plugin {plugin_name}: {e}")
            self.plugin_map = {}

    def update(self):
        """Hlavní smyčka čtení dat."""
        if not self._client.connect():
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
