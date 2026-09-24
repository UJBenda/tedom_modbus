"""Plugin pro Tedom s řídicí jednotkou ComAp InteliCompact (dle tabulky 584-generator.TXT).

Registry se zapisují tak, jak jsou v tabulce z GenConfigu (např. 40021).
Adresa v Modbus rámci = registr - REGISTER_BASE (ComAp: 40001 -> adresa 0).

Typy z tabulky:
  Unsigned, délka 2 B -> "uint16"     Integer, délka 2 B -> "int16"
  Unsigned, délka 4 B -> "uint32"     Integer, délka 4 B -> "int32"
  Dec = počet desetinných míst -> scale = 10^-Dec
"""
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)

REGISTER_BASE = 40001

MEAS = SensorStateClass.MEASUREMENT
TOTAL = SensorStateClass.TOTAL_INCREASING

# Table#1 – stav motoru / stav stykače
STATE_TABLE = {
    25: "Inicializ", 26: "Připraven", 27: "Nepřiprav", 28: "Předstart", 29: "Spouštění",
    30: "Pauza", 31: "Startuje", 32: "Běží", 33: "Zatížen", 34: "Odlehčuje",
    35: "Chlazení", 36: "PomStop", 37: "HavStop", 38: "Ventilace", 39: "PohotMAN",
    40: "Zatěžuje", 41: "ČekáNaStp", 42: "Prohřev", 43: "Odlehčení", 44: "Inicializ",
    45: "Styk. VYP", 46: "OstrProv.", 47: "SíťProvoz", 48: "ProvParal", 49: "ZpětSynch",
    50: "Fázování", 51: "VýpadSítě", 52: "Start Zpo", 53: "NávratSíť", 54: "ParalOstr",
    55: "ParalSit", 56: "PohotMAN", 57: "ŽádnýČas.", 58: "StSíť ZAP", 59: "NávratZpo",
    60: "Přech Zpo", 61: "Volnoběh", 62: "MinStabČa", 63: "MaxStabČa", 64: "Dochlaz.",
    65: "StGenOtev", 66: "StopVenti", 67: "VypšOtSty", 68: "VypršČsyn", 69: "StartSync",
    70: "VentPlyn", 71: "PříšStart", 72: "PříštStop", 73: "StartSyst", 74: "StopSyst",
    75: "Prohřev", 76: "OdlehStop", 77: "Žádný", 78: "Prohřev", 79: "KonstVýk",
    80: "IMP/EXP",
}


def _s(register, name, unit=None, scale=1, precision=0, device_class=None,
       state_class=MEAS, icon=None, register_type="int16", **extra):
    return {
        "register": register,
        "name": name,
        "unit": unit,
        "scale": scale,
        "precision": precision,
        "device_class": device_class,
        "state_class": state_class,
        "icon": icon,
        "register_type": register_type,
        **extra,
    }


V, A, KW, HZ, C = (
    UnitOfElectricPotential.VOLT,
    UnitOfElectricCurrent.AMPERE,
    UnitOfPower.KILO_WATT,
    UnitOfFrequency.HERTZ,
    UnitOfTemperature.CELSIUS,
)
VOLT, CURR, POW, FREQ, TEMP = (
    SensorDeviceClass.VOLTAGE,
    SensorDeviceClass.CURRENT,
    SensorDeviceClass.POWER,
    SensorDeviceClass.FREQUENCY,
    SensorDeviceClass.TEMPERATURE,
)

# Mapa registrů – klíč: parametry senzoru
PLUGIN_MAP = {
    # --- Generátor ---
    "gen_voltage_l1": _s(40009, "Ugen L1-N", V, device_class=VOLT, register_type="uint16"),
    "gen_voltage_l2": _s(40010, "Ugen L2-N", V, device_class=VOLT, register_type="uint16"),
    "gen_voltage_l3": _s(40011, "Ugen L3-N", V, device_class=VOLT, register_type="uint16"),
    "gen_voltage_l1_l2": _s(40014, "Ugen L1-L2", V, device_class=VOLT, register_type="uint16"),
    "gen_voltage_l2_l3": _s(40015, "Ugen L2-L3", V, device_class=VOLT, register_type="uint16"),
    "gen_voltage_l3_l1": _s(40016, "Ugen L3-L1", V, device_class=VOLT, register_type="uint16"),
    "gen_current_l1": _s(40017, "Igen L1", A, device_class=CURR, register_type="uint16"),
    "gen_current_l2": _s(40018, "Igen L2", A, device_class=CURR, register_type="uint16"),
    "gen_current_l3": _s(40019, "Igen L3", A, device_class=CURR, register_type="uint16"),
    "gen_frequency": _s(40022, "Frekvence generátoru", HZ, 0.1, 1, FREQ, register_type="uint16"),
    "power_active": _s(40028, "Činný výkon generátoru", KW, 0.1, 1, POW, icon="mdi:lightning-bolt"),
    "power_active_l1": _s(40029, "Činný výkon gen. L1", KW, 0.1, 1, POW),
    "power_active_l2": _s(40030, "Činný výkon gen. L2", KW, 0.1, 1, POW),
    "power_active_l3": _s(40031, "Činný výkon gen. L3", KW, 0.1, 1, POW),
    "power_reactive": _s(40032, "Jalový výkon generátoru", "kvar", 0.1, 1, icon="mdi:sine-wave"),
    "power_factor": _s(40036, "Účiník generátoru", None, 0.01, 2, SensorDeviceClass.POWER_FACTOR),
    "power_apparent": _s(40045, "Zdánlivý výkon generátoru", "kVA", 0.1, 1, icon="mdi:flash"),
    "power_setpoint": _s(40113, "Žádaný výkon", KW, 0.1, 1, POW, icon="mdi:target"),

    # --- Síť ---
    "mains_voltage_l1": _s(40049, "Usíť L1-N", V, device_class=VOLT, register_type="uint16"),
    "mains_voltage_l2": _s(40050, "Usíť L2-N", V, device_class=VOLT, register_type="uint16"),
    "mains_voltage_l3": _s(40051, "Usíť L3-N", V, device_class=VOLT, register_type="uint16"),
    "mains_frequency": _s(40056, "Frekvence sítě", HZ, 0.1, 1, FREQ, register_type="uint16"),
    "mains_power_import": _s(40058, "Výkon ze sítě", KW, 0.1, 1, POW, icon="mdi:transmission-tower"),
    "load_power": _s(40059, "Činný výkon zátěže", KW, 0.1, 1, POW, icon="mdi:home-lightning-bolt"),

    # --- Motor ---
    "rpm": _s(40021, "Otáčky motoru", "rpm", icon="mdi:speedometer", register_type="uint16"),
    "coolant_temp": _s(40230, "Teplota vody", C, device_class=TEMP, icon="mdi:thermometer"),
    "coolant_temp_secondary": _s(40231, "Teplota sekundární vody", C, device_class=TEMP, icon="mdi:thermometer"),
    "temp_section_1": _s(40232, "Teplota SEKCE 1", C, device_class=TEMP, icon="mdi:thermometer"),
    "temp_section_2": _s(40233, "Teplota SEKCE 2", C, device_class=TEMP, icon="mdi:thermometer"),
    "lambda_voltage": _s(40185, "Lambda", UnitOfElectricPotential.MILLIVOLT, 0.1, 1, VOLT, icon="mdi:gauge"),
    "water_temp_regulation": _s(40192, "Regulace teploty vody", icon="mdi:valve"),

    # --- Řídicí systém ---
    "battery_voltage": _s(40061, "Napětí baterie", V, 0.1, 1, VOLT, icon="mdi:car-battery"),
    "controller_temp": _s(40235, "Teplota procesoru", C, 0.1, 1, TEMP, icon="mdi:chip"),

    # --- Stavy ---
    "status_id": _s(40083, "Stav motoru", device_class=SensorDeviceClass.ENUM, state_class=None,
                    icon="mdi:engine", register_type="uint16", value_map=STATE_TABLE),
    "breaker_status": _s(40084, "Stav stykače", device_class=SensorDeviceClass.ENUM, state_class=None,
                         icon="mdi:electric-switch", register_type="uint16", value_map=STATE_TABLE),
    "timer_value": _s(40086, "Hodnota časovače", UnitOfTime.SECONDS, device_class=SensorDeviceClass.DURATION,
                      icon="mdi:timer-outline", register_type="uint16"),

    # --- Statistika ---
    "run_hours": _s(43001, "Motohodiny", UnitOfTime.HOURS, state_class=TOTAL,
                    icon="mdi:clock-outline", register_type="int32"),
    "service_time": _s(43004, "Čas do servisu", UnitOfTime.HOURS, icon="mdi:wrench-clock"),
    "start_count": _s(43006, "Počet startů", state_class=TOTAL, icon="mdi:counter", register_type="uint16"),
    "energy_active": _s(43007, "Činná energie", UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY,
                        state_class=TOTAL, icon="mdi:lightning-bolt-circle", register_type="int32"),
    "energy_reactive": _s(43009, "Jalová energie", "kvarh", state_class=TOTAL, icon="mdi:sine-wave",
                          register_type="int32"),
    "normal_stops": _s(43011, "Počet běžných stopů", state_class=TOTAL, icon="mdi:counter", register_type="uint32"),
    "emergency_stops": _s(43013, "Počet havarijních stopů", state_class=TOTAL, icon="mdi:alert-octagon",
                          register_type="uint32"),
}
