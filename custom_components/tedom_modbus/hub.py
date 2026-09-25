import logging
import importlib
import inspect
import threading
from pymodbus.client import ModbusTcpClient
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)

# pymodbus 3.10+ přejmenoval parametr "slave" na "device_id"
_UNIT_KWARG = (
    "device_id"
    if "device_id" in inspect.signature(ModbusTcpClient.read_holding_registers).parameters
    else "slave"
)
_UNIT_ID = 1

# ComAp: příkazy se zapisují jedním zápisem do 46359-46360 (argument) + 46361 (příkaz)
COMMAND_REGISTER = 46359


class TedomHub:
    def __init__(self, hass: HomeAssistant, name, host, port, scan_interval, plugin_name):
        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self._client = ModbusTcpClient(host=host, port=port)
        # Čtení (koordinátor) a zápisy (tlačítka) běží v různých vláknech executoru
        self._lock = threading.Lock()
        self._scan_interval = scan_interval
        self._plugin_name = plugin_name
        self.plugin_map = {}
        self.select_map = {}
        self.number_map = {}
        self.button_map = {}
        self.register_base = 0
        self.word_order = "big"
        self.data = {}
        self.coordinator = None

    async def async_init(self):
        """Asynchronní inicializace - bezpečné načtení pluginu."""
        def load_plugin():
            try:
                return importlib.import_module(f".{self._plugin_name}", __package__)
            except ImportError as e:
                _LOGGER.error(f"Tedom: Nelze načíst plugin '{self._plugin_name}'. Chyba: {e}")
            except Exception as e:
                _LOGGER.error(f"Tedom: Chyba v pluginu '{self._plugin_name}': {e}")
            return None

        # Spustíme import v "executoru", aby neblokoval smyčku HA
        module = await self._hass.async_add_executor_job(load_plugin)
        if module is None:
            return

        self.plugin_map = getattr(module, "PLUGIN_MAP", {})
        self.select_map = getattr(module, "SELECT_MAP", {})
        self.number_map = getattr(module, "NUMBER_MAP", {})
        self.button_map = getattr(module, "BUTTON_MAP", {})
        self.register_base = getattr(module, "REGISTER_BASE", 0)
        self.word_order = getattr(module, "WORD_ORDER", "big")
        _LOGGER.info(f"Tedom: Úspěšně načten plugin {self._plugin_name} s {len(self.plugin_map)} registry.")

    def _address(self, info):
        return info["register"] - self.register_base if "register" in info else info["address"]

    def _data_type(self, info):
        return getattr(self._client.DATATYPE, info.get("register_type", "int16").upper())

    def _connect(self):
        if not self._client.connect():
            raise ConnectionError(f"Tedom: Nelze se připojit k {self._host}:{self._port}")

    def update(self):
        """Hlavní smyčka čtení dat (běží v executoru)."""
        read_map = {**self.plugin_map, **self.select_map, **self.number_map}
        if not read_map:
            return self.data

        data = {}
        with self._lock:
            try:
                self._connect()
            except ConnectionError as e:
                self.data = {}
                raise UpdateFailed(str(e)) from e

            try:
                for key, info in read_map.items():
                    data_type = self._data_type(info)
                    try:
                        # Comap používá Holding registry
                        result = self._client.read_holding_registers(
                            self._address(info), count=data_type.value[1], **{_UNIT_KWARG: _UNIT_ID}
                        )
                        if result.isError():
                            _LOGGER.debug(f"Tedom: Chyba čtení {key}: {result}")
                            continue

                        val = self._client.convert_from_registers(
                            result.registers,
                            data_type=data_type,
                            word_order=info.get("word_order", self.word_order),
                        )
                        # Aplikace měřítka
                        data[key] = val * info.get("scale", 1)
                    except Exception as e:
                        _LOGGER.debug(f"Tedom: Chyba čtení {key}: {e}")
            finally:
                self._client.close()

        self.data = data
        return data

    def _write(self, address, registers):
        """Zápis registrů funkcí 16 (běží v executoru, drží zámek)."""
        self._connect()
        try:
            result = self._client.write_registers(address, registers, **{_UNIT_KWARG: _UNIT_ID})
            if result.isError():
                raise HomeAssistantError(f"Tedom: Controller odmítl zápis na adresu {address}: {result}")
        finally:
            self._client.close()

    def write_value(self, info, value):
        """Zápis hodnoty (setpoint / režim) do registru podle definice v pluginu."""
        data_type = self._data_type(info)
        raw = int(round(value / info.get("scale", 1)))
        registers = self._client.convert_to_registers(
            raw, data_type=data_type, word_order=info.get("word_order", self.word_order)
        )
        with self._lock:
            try:
                self._write(self._address(info), registers)
            except ConnectionError as e:
                raise HomeAssistantError(str(e)) from e

    def send_command(self, argument, expected_return):
        """Odešle ComAp příkaz (start, stop, reset...) a ověří odpověď controlleru."""
        address = COMMAND_REGISTER - 40001
        with self._lock:
            try:
                self._connect()
            except ConnectionError as e:
                raise HomeAssistantError(str(e)) from e
            try:
                result = self._client.write_registers(
                    address, [argument >> 16, argument & 0xFFFF, 1], **{_UNIT_KWARG: _UNIT_ID}
                )
                if result.isError():
                    raise HomeAssistantError(f"Tedom: Controller odmítl příkaz: {result}")

                # Controller přepíše argument návratovou hodnotou, pokud příkaz provedl
                result = self._client.read_holding_registers(address, count=2, **{_UNIT_KWARG: _UNIT_ID})
                if result.isError():
                    raise HomeAssistantError(f"Tedom: Nelze ověřit provedení příkazu: {result}")
                returned = (result.registers[0] << 16) | result.registers[1]
            finally:
                self._client.close()

        if returned != expected_return:
            raise HomeAssistantError(
                f"Tedom: Controller příkaz neprovedl (vráceno 0x{returned:08X}, "
                f"očekáváno 0x{expected_return:08X}). Zkontrolujte režim (MAN) a přístupová práva."
            )

    def close(self):
        self._client.close()
