"""Plugin pro Tedom InteliCompact s User Table (dle souboru 117.TXT)."""
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfPower,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfSpeed,
    UnitOfTime,
)

# Mapa registrů
# Struktura: klíč: {address, name, unit, scale, ...}
PLUGIN_MAP = {
    "rpm": {
        "address": 21,
        "name": "Otáčky Motoru",
        "unit": UnitOfSpeed.RPM,
        "scale": 1,
        "precision": 0,
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:speedometer",
    },
    "power_active": {
        "address": 28,
        "name": "Výkon Generátoru",
        "unit": UnitOfPower.KILO_WATT,
        "scale": 0.1,   # Dim 1 v TXT = děleno 10
        "precision": 1,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:lightning-bolt",
    },
    "battery_voltage": {
        "address": 61,
        "name": "Napětí Baterie",
        "unit": UnitOfElectricPotential.VOLT,
        "scale": 0.1,
        "precision": 1,
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:car-battery",
    },
    "coolant_temp": {
        "address": 230,
        "name": "Teplota Vody",
        "unit": UnitOfTemperature.CELSIUS,
        "scale": 1,
        "precision": 0,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:thermometer",
    },
    "run_hours": {
        "address": 3001, # Pozor, ověřit zda 32bit nebo 16bit. Zde předpoklad 32bit.
        "name": "Motohodiny",
        "unit": UnitOfTime.HOURS,
        "scale": 1,
        "precision": 0,
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:clock-outline",
        "register_type": "uint32", # Speciální flag pro 32bit
    },
    "status_id": {
        "address": 83,
        "name": "Stav Jednotky",
        "unit": None,
        "scale": 1,
        "precision": 0,
        "device_class": SensorDeviceClass.ENUM,
        "icon": "mdi:engine",
        # Mapování stavů přímo v pluginu (Wills106 styl)
        "value_map": {
            24: "Ready",
            27: "Cranking",
            30: "Running",
            31: "Loaded",
            33: "Cooling",
            34: "Stop",
            54: "Emergency Man",
            55: "No Timer",
            58: "Trans Del",
            62: "AfterCool",
        }
    }
}
