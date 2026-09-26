from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE, UnitOfPower, UnitOfElectricPotential, UnitOfElectricCurrent,
    UnitOfTemperature, UnitOfFrequency, UnitOfTime, UnitOfEnergy,
)
import dataclasses

from .const import (
    GEN_TYPE_SYNC,
    TedomSensorEntityDescription, TedomButtonEntityDescription, 
    TedomSelectEntityDescription, TedomNumberEntityDescription,
    REGISTER_U16, REGISTER_S16, REGISTER_U32, REGISTER_S32
)
# Kompletní mapa stavů podle ComAp Tabulky 1 (pouze pro Stav motoru)
FULL_STATE_MAP = {
    23: "Init", 24: "Připraven", 25: "Nepřipraven", 26: "Předstart", 
    27: "Startování", 28: "Pauza", 29: "Startování", 30: "Běží", 
    31: "Zatížen", 32: "Odpínání", 33: "Chlazení", 34: "Zastaveno", 
    35: "HavStop", 36: "Ventil", 37: "Nouzový prov.", 38: "Měkké zatíž.", 
    39: "Čeká na stop", 40: "Zahřívání", 41: "Bez zátěže", 42: "Init", 
    43: "Vypínání jističe", 44: "Ostrovní prov.", 45: "Síťový prov.", 
    46: "Paralelní síť", 47: "RevSync", 48: "Synchronizace", 
    49: "Porucha sítě", 50: "Čeká na start", 51: "Návrat sítě", 
    55: "Bez časovače", 71: "Syst. Start", 72: "Syst. Stop", 73: "Zahřívání"
}

# Synchronní generátor (export 584-generator.TXT): Table#1 – stav motoru / stykače
SYNC_STATE_MAP = {
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

# Režimy (registr 43204): synchronní dle List#7, asynchronní ověřeno na jednotce
SYNC_MODE_MAP = {"VYP": 0, "MAN": 1, "SEM": 2, "AUT": 3}


class TedomPlugin:
    NAME = "Tedom Cogeneration"

    def __init__(self, gen_type=None):
        """Číselníky režimů a stavů podle typu generátoru (výchozí = asynchronní)."""
        self.gen_type = gen_type
        if gen_type == GEN_TYPE_SYNC:
            self.SENSOR_TYPES = [
                dataclasses.replace(d, value_map=SYNC_STATE_MAP)
                if d.key in ("engine_state", "breaker_state") else d
                for d in self.SENSOR_TYPES
            ]
            self.SELECT_TYPES = [
                dataclasses.replace(d, options_map=SYNC_MODE_MAP) if d.key == "mode_selector" else d
                for d in self.SELECT_TYPES
            ]

    # Adresa = číslo registru z tabulky GenConfigu − 40001 (např. 40021 → 20).
    # interval_group: 1 = každý cyklus, 2 = cca 1× za minutu, 3 = cca 1× za 10 minut.
    # Entity s enabled=False jsou v HA ve výchozím stavu vypnuté (dají se zapnout v nastavení entity).

    SENSOR_TYPES = [
        # === VÝKON A ELEKTRIKA (ověřeno na jednotce) ===
        TedomSensorEntityDescription(key="p_gen_total", name="Aktuální výkon", address=27, native_unit_of_measurement=UnitOfPower.KILO_WATT, scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, icon="mdi:lightning-bolt", interval_group=1),
        TedomSensorEntityDescription(key="rpm", name="Otáčky motoru", address=20, native_unit_of_measurement="ot/m", icon="mdi:speedometer", state_class=SensorStateClass.MEASUREMENT, interval_group=1),
        TedomSensorEntityDescription(key="gen_freq", name="Frekvence Gen", address=21, native_unit_of_measurement=UnitOfFrequency.HERTZ, scale=0.1, suggested_display_precision=1, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, interval_group=1),
        TedomSensorEntityDescription(key="ugen_l1_n", name="Napětí Gen L1", address=8, native_unit_of_measurement=UnitOfElectricPotential.VOLT, suggested_display_precision=0, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, interval_group=1),
        TedomSensorEntityDescription(key="ugen_l2_n", name="Napětí Gen L2", address=9, native_unit_of_measurement=UnitOfElectricPotential.VOLT, suggested_display_precision=0, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, interval_group=1),
        TedomSensorEntityDescription(key="ugen_l3_n", name="Napětí Gen L3", address=10, native_unit_of_measurement=UnitOfElectricPotential.VOLT, suggested_display_precision=0, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, interval_group=1),
        TedomSensorEntityDescription(key="igen_l1", name="Proud Gen L1", address=16, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, suggested_display_precision=0, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, interval_group=1),
        TedomSensorEntityDescription(key="igen_l2", name="Proud Gen L2", address=17, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, suggested_display_precision=0, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, interval_group=1),
        TedomSensorEntityDescription(key="igen_l3", name="Proud Gen L3", address=18, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, suggested_display_precision=0, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, interval_group=1),

        # === VÝKON DETAIL (40029–40045) ===
        TedomSensorEntityDescription(key="p_gen_l1", name="Výkon Gen L1", address=28, native_unit_of_measurement=UnitOfPower.KILO_WATT, scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, interval_group=1, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="p_gen_l2", name="Výkon Gen L2", address=29, native_unit_of_measurement=UnitOfPower.KILO_WATT, scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, interval_group=1, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="p_gen_l3", name="Výkon Gen L3", address=30, native_unit_of_measurement=UnitOfPower.KILO_WATT, scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, interval_group=1, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="q_gen_total", name="Jalový výkon", address=31, native_unit_of_measurement="kvar", scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, state_class=SensorStateClass.MEASUREMENT, icon="mdi:sine-wave", interval_group=1, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="power_factor", name="Účiník", address=35, scale=0.01, suggested_display_precision=2, data_type=REGISTER_S16, device_class=SensorDeviceClass.POWER_FACTOR, state_class=SensorStateClass.MEASUREMENT, interval_group=1),
        TedomSensorEntityDescription(key="s_gen_total", name="Zdánlivý výkon", address=44, native_unit_of_measurement="kVA", scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, state_class=SensorStateClass.MEASUREMENT, icon="mdi:flash", interval_group=1, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="ugen_l1_l2", name="Napětí Gen L1-L2", address=13, native_unit_of_measurement=UnitOfElectricPotential.VOLT, suggested_display_precision=0, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, interval_group=2, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="ugen_l2_l3", name="Napětí Gen L2-L3", address=14, native_unit_of_measurement=UnitOfElectricPotential.VOLT, suggested_display_precision=0, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, interval_group=2, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="ugen_l3_l1", name="Napětí Gen L3-L1", address=15, native_unit_of_measurement=UnitOfElectricPotential.VOLT, suggested_display_precision=0, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, interval_group=2, entity_registry_enabled_default=False),

        # === SÍŤ A SPOTŘEBA (40049–40059) ===
        TedomSensorEntityDescription(key="p_mains", name="Výkon ze sítě", address=57, native_unit_of_measurement=UnitOfPower.KILO_WATT, scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, icon="mdi:transmission-tower", interval_group=1),
        TedomSensorEntityDescription(key="p_load", name="Výkon zátěže", address=58, native_unit_of_measurement=UnitOfPower.KILO_WATT, scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, icon="mdi:home-lightning-bolt", interval_group=1),
        TedomSensorEntityDescription(key="umains_l1_n", name="Napětí sítě L1", address=48, native_unit_of_measurement=UnitOfElectricPotential.VOLT, suggested_display_precision=0, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, icon="mdi:transmission-tower", interval_group=2),
        TedomSensorEntityDescription(key="umains_l2_n", name="Napětí sítě L2", address=49, native_unit_of_measurement=UnitOfElectricPotential.VOLT, suggested_display_precision=0, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, icon="mdi:transmission-tower", interval_group=2),
        TedomSensorEntityDescription(key="umains_l3_n", name="Napětí sítě L3", address=50, native_unit_of_measurement=UnitOfElectricPotential.VOLT, suggested_display_precision=0, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, icon="mdi:transmission-tower", interval_group=2),
        TedomSensorEntityDescription(key="mains_freq", name="Frekvence sítě", address=55, native_unit_of_measurement=UnitOfFrequency.HERTZ, scale=0.1, suggested_display_precision=1, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, interval_group=2),

        # === TEPLOTY A MOTOR ===
        TedomSensorEntityDescription(key="water_temp", name="Teplota vody", address=229, native_unit_of_measurement=UnitOfTemperature.CELSIUS, suggested_display_precision=0, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, data_type=REGISTER_S16, interval_group=2),
        TedomSensorEntityDescription(key="water_temp_sec", name="Teplota sekundární vody", address=230, native_unit_of_measurement=UnitOfTemperature.CELSIUS, suggested_display_precision=0, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, data_type=REGISTER_S16, interval_group=2),
        TedomSensorEntityDescription(key="temp_section_1", name="Teplota SEKCE 1", address=231, native_unit_of_measurement=UnitOfTemperature.CELSIUS, suggested_display_precision=0, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, data_type=REGISTER_S16, interval_group=2),
        TedomSensorEntityDescription(key="temp_section_2", name="Teplota SEKCE 2", address=232, native_unit_of_measurement=UnitOfTemperature.CELSIUS, suggested_display_precision=0, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, data_type=REGISTER_S16, interval_group=2),
        TedomSensorEntityDescription(key="temp_compensation", name="Kompenzační teplota", address=233, native_unit_of_measurement=UnitOfTemperature.CELSIUS, suggested_display_precision=0, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, data_type=REGISTER_S16, interval_group=2, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="lambda_mv", name="Lambda", address=184, native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT, scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, icon="mdi:gauge", interval_group=2),
        TedomSensorEntityDescription(key="water_temp_reg", name="Regulace teploty vody", address=191, data_type=REGISTER_S16, state_class=SensorStateClass.MEASUREMENT, icon="mdi:valve", interval_group=2, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="battery_volts", name="Napětí baterie", address=60, native_unit_of_measurement=UnitOfElectricPotential.VOLT, scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, icon="mdi:car-battery", interval_group=2),
        TedomSensorEntityDescription(key="d_plus", name="D+", address=62, native_unit_of_measurement=UnitOfElectricPotential.VOLT, scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, interval_group=2, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="cpu_temp", name="Teplota procesoru", address=234, native_unit_of_measurement=UnitOfTemperature.CELSIUS, scale=0.1, suggested_display_precision=1, data_type=REGISTER_S16, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, icon="mdi:chip", interval_group=2, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="gsm_signal", name="Síla signálu GSM", address=201, native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, icon="mdi:signal", interval_group=2, entity_registry_enabled_default=False),

        # === STATISTIKA A ÚDRŽBA (ověřeno: motohodiny, starty, energie) ===
        TedomSensorEntityDescription(key="run_hours", name="Motohodiny", address=3000, native_unit_of_measurement=UnitOfTime.HOURS, data_type=REGISTER_U32, state_class=SensorStateClass.TOTAL_INCREASING, icon="mdi:clock-outline", interval_group=3),
        TedomSensorEntityDescription(key="starts_count", name="Počet startů", address=3005, state_class=SensorStateClass.TOTAL_INCREASING, icon="mdi:counter", interval_group=3),
        TedomSensorEntityDescription(key="active_energy", name="Vyrobená energie", address=3006, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, suggested_display_precision=0, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, data_type=REGISTER_U32, interval_group=3),
        TedomSensorEntityDescription(key="reactive_energy", name="Jalová energie", address=3008, native_unit_of_measurement="kvarh", data_type=REGISTER_S32, state_class=SensorStateClass.TOTAL_INCREASING, icon="mdi:sine-wave", interval_group=3, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="service_time", name="Čas do servisu", address=3003, native_unit_of_measurement=UnitOfTime.HOURS, data_type=REGISTER_S16, icon="mdi:wrench-clock", interval_group=3),
        TedomSensorEntityDescription(key="service_time_2", name="Čas do servisu 2", address=3004, native_unit_of_measurement=UnitOfTime.HOURS, data_type=REGISTER_S16, icon="mdi:wrench-clock", interval_group=3, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="normal_stops", name="Počet běžných stopů", address=3010, data_type=REGISTER_U32, state_class=SensorStateClass.TOTAL_INCREASING, icon="mdi:counter", interval_group=3, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="emergency_stops", name="Počet havarijních stopů", address=3012, data_type=REGISTER_U32, state_class=SensorStateClass.TOTAL_INCREASING, icon="mdi:alert-octagon-outline", interval_group=3),
        TedomSensorEntityDescription(key="nominal_power", name="Jmenovitý výkon", address=3037, native_unit_of_measurement=UnitOfPower.KILO_WATT, scale=0.1, suggested_display_precision=1, device_class=SensorDeviceClass.POWER, icon="mdi:information-outline", interval_group=3),
        TedomSensorEntityDescription(key="fw_version", name="Verze FW", address=87, scale=0.1, suggested_display_precision=1, icon="mdi:chip", interval_group=3, entity_registry_enabled_default=False),

        # === STAVY ===
        TedomSensorEntityDescription(key="engine_state", name="Stav motoru", address=82, icon="mdi:engine", interval_group=1, value_map=FULL_STATE_MAP),
        TedomSensorEntityDescription(key="breaker_state", name="Stav jističe", address=83, icon="mdi:electric-switch", interval_group=1, value_map=FULL_STATE_MAP),
        TedomSensorEntityDescription(key="timer_value", name="Zbývající čas časovače", address=85, native_unit_of_measurement=UnitOfTime.SECONDS, device_class=SensorDeviceClass.DURATION, icon="mdi:timer-outline", interval_group=1),
        TedomSensorEntityDescription(key="ecu_fault_count", name="Aktivní poruchy ECU", address=7068, icon="mdi:engine-off", state_class=SensorStateClass.MEASUREMENT, interval_group=2),

        # === BINÁRNÍ VSTUPY (40072, Binary#1) ===
        TedomSensorEntityDescription(key="ext_start_stop", name="Externí Start/Stop", address=71, bitmask=0x01, value_map={0: "VYPNUTO", 1: "ZAPNUTO"}, icon="mdi:power-plug", interval_group=1),
        # Bit 1 je dle tabulky vstup "Centrální stop" (klíč ponechán kvůli historii)
        TedomSensorEntityDescription(key="emergency_stop", name="Centrální stop", address=71, bitmask=0x02, value_map={0: "Neaktivní", 1: "Aktivní"}, icon="mdi:alert-octagon", interval_group=1),
        TedomSensorEntityDescription(key="gcb_feedback", name="Stykač generátoru (zpětná vazba)", address=71, bitmask=0x04, value_map={0: "Rozepnut", 1: "Sepnut"}, icon="mdi:electric-switch", interval_group=1),
        TedomSensorEntityDescription(key="mcb_feedback", name="Stykač sítě (zpětná vazba)", address=71, bitmask=0x08, value_map={0: "Rozepnut", 1: "Sepnut"}, icon="mdi:electric-switch", interval_group=1),
        TedomSensorEntityDescription(key="overcurrent", name="Nadproud generátoru", address=71, bitmask=0x10, value_map={0: "OK", 1: "AKTIVNÍ"}, icon="mdi:current-ac", interval_group=1),
        TedomSensorEntityDescription(key="oil_pressure", name="Tlak oleje", address=71, bitmask=0x20, value_map={0: "OK", 1: "NÍZKÝ"}, icon="mdi:oil", interval_group=1),
        TedomSensorEntityDescription(key="oil_level", name="Hladina oleje", address=71, bitmask=0x80, value_map={0: "OK", 1: "NÍZKÁ"}, icon="mdi:oil-level", interval_group=1),
        TedomSensorEntityDescription(key="ext_npu", name="Externí NPU", address=71, bitmask=0x100, value_map={0: "OK", 1: "AKTIVNÍ"}, icon="mdi:shield-alert", interval_group=1, entity_registry_enabled_default=False),

        # === BINÁRNÍ VÝSTUPY (40073, Binary#2) ===
        TedomSensorEntityDescription(key="warning", name="Výstraha", address=72, bitmask=0x40, value_map={0: "OK", 1: "AKTIVNÍ"}, icon="mdi:alert", interval_group=1),
        TedomSensorEntityDescription(key="fuel_valve", name="Ventil paliva", address=72, bitmask=0x04, value_map={0: "Zavřen", 1: "Otevřen"}, icon="mdi:valve", interval_group=1),
        TedomSensorEntityDescription(key="gcb_output", name="Stykač generátoru", address=72, bitmask=0x08, value_map={0: "Vypnut", 1: "Zapnut"}, icon="mdi:electric-switch", interval_group=1),
        TedomSensorEntityDescription(key="starter", name="Startér", address=72, bitmask=0x01, value_map={0: "Vypnut", 1: "Zapnut"}, icon="mdi:engine", interval_group=1, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="ignition", name="Zapalování", address=72, bitmask=0x02, value_map={0: "Vypnuto", 1: "Zapnuto"}, icon="mdi:flash", interval_group=1, entity_registry_enabled_default=False),

        # === ECU A ČERPADLA (40151 Binary#4, 40168 Binary#5) ===
        TedomSensorEntityDescription(key="ecu_yellow", name="ECU žlutá lampa", address=150, bitmask=0x01, value_map={0: "Nesvítí", 1: "Svítí"}, icon="mdi:alarm-light-outline", interval_group=2),
        TedomSensorEntityDescription(key="ecu_red", name="ECU červená lampa", address=150, bitmask=0x02, value_map={0: "Nesvítí", 1: "Svítí"}, icon="mdi:alarm-light", interval_group=2),
        TedomSensorEntityDescription(key="pump_parallel", name="Čerpadlo paralel", address=167, bitmask=0x04, value_map={0: "Vypnuto", 1: "Zapnuto"}, icon="mdi:pump", interval_group=1),
        TedomSensorEntityDescription(key="pump_island", name="Čerpadlo ostrov", address=167, bitmask=0x08, value_map={0: "Vypnuto", 1: "Zapnuto"}, icon="mdi:pump", interval_group=1, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="cool_more", name="Chlaď více", address=167, bitmask=0x01, value_map={0: "Ne", 1: "Ano"}, icon="mdi:snowflake", interval_group=1, entity_registry_enabled_default=False),
        TedomSensorEntityDescription(key="cool_less", name="Chlaď méně", address=167, bitmask=0x02, value_map={0: "Ne", 1: "Ano"}, icon="mdi:snowflake-off", interval_group=1, entity_registry_enabled_default=False),
    ]

    SELECT_TYPES = [
        # Opravené mapování režimů přesně podle List #5 (Tento stroj MAN vůbec nemá)
        TedomSelectEntityDescription(key="mode_selector", name="Režim stroje", address=3203, options_map={"VYP": 0, "SEM": 1, "AUT": 2}, icon="mdi:state-machine"),
    ]

    BUTTON_TYPES = [
        TedomButtonEntityDescription(key="cmd_fault_reset", name="Reset poruch", address=409, payload=1, icon="mdi:alert-remove"), # Funkční
        # ComAp příkazy přes registry 46359-46361 (funguje v SEM/MAN, v AUT je controller ignoruje)
        TedomButtonEntityDescription(key="cmd_engine_start", name="Start motoru", command=0x01FE0000, command_return=0x000001FF, icon="mdi:play"),
        TedomButtonEntityDescription(key="cmd_engine_stop", name="Stop motoru", command=0x02FD0000, command_return=0x000002FE, icon="mdi:stop"),
    ]

    NUMBER_TYPES = [
        # 43020 "KonstVýkon" (kW, 1 desetinné místo) – dřív chybně 43200, který v tabulce není
        TedomNumberEntityDescription(key="req_power", name="Požadovaný výkon", address=3019, native_unit_of_measurement=UnitOfPower.KILO_WATT, scale=0.1, native_step=0.1, data_type=REGISTER_S16, native_min_value=0, native_max_value=3200, icon="mdi:tune-vertical"),
        # 43334 "PožadTeplVody"
        TedomNumberEntityDescription(key="req_temp", name="Požadovaná teplota", address=3333, native_unit_of_measurement=UnitOfTemperature.CELSIUS, scale=1.0, data_type=REGISTER_S16, native_min_value=0, native_max_value=100, icon="mdi:thermometer-water"),
    ]
