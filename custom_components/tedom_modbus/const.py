import logging
from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.number import NumberEntityDescription
from homeassistant.const import CONF_SCAN_INTERVAL

DOMAIN = "tedom_modbus"
CONF_NAME = "name"
CONF_MODBUS_ADDR = "modbus_address"

# Klíče pro nastavení tří různých intervalů čtení
CONF_SCAN_INTERVAL_2 = "scan_interval_2"
CONF_SCAN_INTERVAL_3 = "scan_interval_3"

# Typ generátoru – určuje číselník režimů a stavů
CONF_GEN_TYPE = "generator_type"
GEN_TYPE_ASYNC = "async"  # asynchronní: režimy VYP/SEM/AUT (bez MAN)
GEN_TYPE_SYNC = "sync"    # synchronní (např. 584): režimy VYP/MAN/SEM/AUT dle List#7
GEN_TYPES = {
    GEN_TYPE_ASYNC: "Asynchronní generátor (VYP / SEM / AUT)",
    GEN_TYPE_SYNC: "Synchronní generátor (VYP / MAN / SEM / AUT)",
}

DEFAULT_NAME = "Tedom"
DEFAULT_PORT = 502
DEFAULT_MODBUS_ADDR = 1

# Výchozí časy pro skupiny (v sekundách)
DEFAULT_SCAN_INTERVAL = 10     # Interval 1: Rychlá data
DEFAULT_SCAN_INTERVAL_2 = 60   # Interval 2: Střední data
DEFAULT_SCAN_INTERVAL_3 = 600  # Interval 3: Pomalá data

# Datové typy Modbus registrů
REGISTER_U16 = "uint16"
REGISTER_S16 = "int16"
REGISTER_U32 = "uint32"
REGISTER_S32 = "int32"

_LOGGER = logging.getLogger(__name__)

@dataclass
class TedomSensorEntityDescription(SensorEntityDescription):
    """Popis senzoru pro čtení hodnot."""
    address: int = 0
    data_type: str = REGISTER_U16
    scale: float = 1.0
    bitmask: int = None
    value_map: dict = None
    precision: int = None
    interval_group: int = 1

@dataclass
class TedomButtonEntityDescription(ButtonEntityDescription):
    """Popis tlačítka pro zápis příkazu (např. Reset)."""
    address: int = 0
    payload: int = 1
    # ComAp příkaz (např. 0x01FE0000 = start) a hodnota, kterou controller vrátí po provedení
    command: int = None
    command_return: int = None

@dataclass
class TedomSelectEntityDescription(SelectEntityDescription):
    """Popis přepínače pro výběr režimu (např. OFF/AUT)."""
    address: int = 0
    options_map: dict = None 
    
@dataclass
class TedomNumberEntityDescription(NumberEntityDescription):
    """Popis číselného nastavení (např. Baseload)."""
    address: int = 0
    scale: float = 1.0
    data_type: str = REGISTER_U16
    native_min_value: float = 0
    native_max_value: float = 32000