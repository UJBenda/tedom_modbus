from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfPower, UnitOfElectricPotential, UnitOfElectricCurrent,
    UnitOfTemperature, UnitOfFrequency, UnitOfTime, UnitOfEnergy,
)
from .const import (
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

class TedomPlugin:
    NAME = "Tedom Cogeneration"

    SENSOR_TYPES = [
        # === VÝKON A ELEKTRIKA (Vše konečně posunuto o -1) ===
        TedomSensorEntityDescription(key="p_gen_total", name="Aktuální výkon", address=27, native_unit_of_measurement=UnitOfPower.KILO_WATT, scale=0.1, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT, interval_group=1), # Funkční (Celkový výkon)
        TedomSensorEntityDescription(key="rpm", name="Otáčky motoru", address=20, native_unit_of_measurement="ot/m", icon="mdi:speedometer", interval_group=1), # Funkční
        
        # Frekvence: Měřítko nastaveno na 0.01 (5000 -> 50.00 Hz)
        TedomSensorEntityDescription(key="gen_freq", name="Frekvence Gen", address=21, native_unit_of_measurement=UnitOfFrequency.HERTZ, scale=0.1, device_class=SensorDeviceClass.FREQUENCY, interval_group=1), # Funkční
        
        TedomSensorEntityDescription(key="ugen_l1_n", name="Napětí Gen L1", address=8, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, interval_group=1), # Funkční
        TedomSensorEntityDescription(key="ugen_l2_n", name="Napětí Gen L2", address=9, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, interval_group=1), # Funkční
        TedomSensorEntityDescription(key="ugen_l3_n", name="Napětí Gen L3", address=10, native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, interval_group=1), # Funkční
        
        TedomSensorEntityDescription(key="igen_l1", name="Proud Gen L1", address=16, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, interval_group=1), # Funkční
        TedomSensorEntityDescription(key="igen_l2", name="Proud Gen L2", address=17, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, interval_group=1), # Funkční
        TedomSensorEntityDescription(key="igen_l3", name="Proud Gen L3", address=18, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, interval_group=1), # Funkční

        # === DIAGNOSTIKA ===
        TedomSensorEntityDescription(key="water_temp", name="Teplota vody", address=229, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, data_type=REGISTER_S16, interval_group=2),
        
        # Baterie: Adresa 60, vrací správně reálné napětí z linuxového výpisu
        TedomSensorEntityDescription(key="battery_volts", name="Napětí baterie", address=60, native_unit_of_measurement=UnitOfElectricPotential.VOLT, scale=0.1, data_type=REGISTER_S16, interval_group=2),

        # === STATISTIKA (100% Funkční podle linuxových testů) ===
        TedomSensorEntityDescription(key="run_hours", name="Motohodiny", address=3000, native_unit_of_measurement=UnitOfTime.HOURS, data_type=REGISTER_U32, state_class=SensorStateClass.TOTAL_INCREASING, interval_group=3), # Funkční
        TedomSensorEntityDescription(key="starts_count", name="Počet startů", address=3005, state_class=SensorStateClass.TOTAL_INCREASING, interval_group=3), # Funkční
        TedomSensorEntityDescription(key="active_energy", name="Vyrobená energie", address=3006, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, data_type=REGISTER_U32, interval_group=3), # Funkční
        
        # === STAVY A ALARMY ===
        # Stav motoru dostal velkou mapu, adresy vráceny na 82 a 83
        TedomSensorEntityDescription(key="engine_state", name="Stav motoru", address=82, interval_group=1, value_map=FULL_STATE_MAP), 
        TedomSensorEntityDescription(key="breaker_state", name="Stav jističe", address=83, interval_group=1, value_map=FULL_STATE_MAP),
        
        # Binární senzory vráceny zpět na 71
        TedomSensorEntityDescription(key="ext_start_stop", name="Externí Start/Stop", address=71, bitmask=0x01, value_map={0: "VYPNUTO", 1: "ZAPNUTO"}, icon="mdi:power-plug", interval_group=1),
        TedomSensorEntityDescription(key="emergency_stop", name="Nouzové zastavení", address=71, bitmask=0x02, value_map={0: "OK", 1: "AKTIVNÍ"}, icon="mdi:alert-octagon", interval_group=1), 
        TedomSensorEntityDescription(key="oil_pressure", name="Tlak oleje", address=71, bitmask=0x20, value_map={0: "OK", 1: "NÍZKÝ"}, icon="mdi:oil", interval_group=1),
        TedomSensorEntityDescription(key="oil_level", name="Hladina oleje", address=71, bitmask=0x80, value_map={0: "OK", 1: "NÍZKÁ"}, icon="mdi:oil-level", interval_group=1),
    ]

    SELECT_TYPES = [
        # Opravené mapování režimů přesně podle List #5 (Tento stroj MAN vůbec nemá)
        TedomSelectEntityDescription(key="mode_selector", name="Režim stroje", address=3203, options_map={"VYP": 0, "SEM": 1, "AUT": 2}), 
    ]

    BUTTON_TYPES = [
        TedomButtonEntityDescription(key="cmd_fault_reset", name="Reset poruch", address=409, payload=1, icon="mdi:alert-remove") # Funkční
    ]

    NUMBER_TYPES = [
        TedomNumberEntityDescription(key="req_power", name="Požadovaný výkon", address=3199, native_unit_of_measurement=UnitOfPower.KILO_WATT, scale=1.0, data_type=REGISTER_S16, min_value=0, max_value=1000),
        TedomNumberEntityDescription(key="req_temp", name="Požadovaná teplota", address=3333, native_unit_of_measurement=UnitOfTemperature.CELSIUS, scale=1.0, data_type=REGISTER_S16, min_value=0, max_value=150) # Funkční
    ]