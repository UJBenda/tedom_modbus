import logging
import struct
from enum import Enum
import inspect
from pymodbus.client import AsyncModbusTcpClient

_LOGGER = logging.getLogger(__name__)

# Detekce správného parametru slave/device_id (pymodbus 3.10+ používá device_id)
ADDR_KW = (
    "device_id"
    if "device_id" in inspect.signature(AsyncModbusTcpClient.read_holding_registers).parameters
    else "slave"
)

class DataType(Enum):
    INT16 = "int16"
    UINT16 = "uint16"
    INT32 = "int32"
    UINT32 = "uint32"
    FLOAT32 = "float32"
    STRING = "string"

def convert_from_registers(registers, data_type: DataType, wordorder="big"):
    """Převede registry na číslo s podporou Word Swap pro ComAp."""
    if not registers:
        return None

    try:
        if data_type == DataType.STRING:
            return "".join([chr(r >> 8) + chr(r & 0xFF) for r in registers]).strip('\x00')

        # Pro 32-bitové hodnoty (2 registry)
        if len(registers) == 2:
            # OPRAVA: Prohození registrů (Word Swap) pro ComAp Endianitu
            # Předtím to dělalo miliardové nesmysly, teď je pořadí správné.
            high_word = registers[0]
            low_word = registers[1]
            combined = (high_word << 16) | low_word
            
            fmt = ">i" if data_type == DataType.INT32 else ">I"
            if data_type == DataType.FLOAT32: fmt = ">f"
            
            return struct.unpack(fmt, struct.pack(">I", combined))[0]

        # Pro 16-bitové hodnoty
        val = registers[0]
        if data_type == DataType.INT16:
            return struct.unpack(">h", struct.pack(">H", val))[0]
        return val

    except Exception as e:
        _LOGGER.error(f"Chyba dekódování registrů: {e}")
        return None