"""Raw Centrometal code -> sensor description, for the BioTec Plus (biopl).

Each entry is [unit, icon, device_class, friendly_name]. Names/units are kept in
sync with the cloud integration (hass-centrometal-boiler) so both read the same
boiler the same way. Codes not listed here are exposed as disabled-by-default
`{?} <code>` sensors, which is how new values are discovered.
"""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime

_C = UnitOfTemperature.CELSIUS
_TEMP = SensorDeviceClass.TEMPERATURE
_MIN = UnitOfTime.MINUTES

# code: [unit, icon, device_class, name]
KNOWN_CODES: dict[str, list] = {
    # --- Temperatures ---
    "B_Tak1_1": [_C, "mdi:thermometer", _TEMP, "Buffer Tank Temperature Up"],
    "B_Tak2_1": [_C, "mdi:thermometer", _TEMP, "Buffer Tank Temperature Down"],
    "B_Tdpl1": [_C, "mdi:thermometer", _TEMP, "Flue Gas"],
    "B_Tpov1": [_C, "mdi:thermometer", _TEMP, "Mixer Temperature"],
    "B_Tk1b": [_C, "mdi:thermometer", _TEMP, "Boiler Temperature Wood"],
    "B_Tk1p": [_C, "mdi:thermometer", _TEMP, "Boiler Temperature Pellet"],
    "B_Tlo1": [_C, "mdi:thermometer", _TEMP, "Firebox Temperature"],
    "B_Tptv1": [_C, "mdi:thermometer", _TEMP, "Domestic Hot Water"],
    "B_Ths1": [_C, "mdi:thermometer", _TEMP, "Hydraulic Crossover Temperature"],
    "B_Tva1": [_C, "mdi:thermometer", _TEMP, "Outdoor Temperature"],
    # --- Misc / actuators ---
    "B_fan": ["rpm", "mdi:fan", None, "Fan"],
    "B_Oxy1": ["% O2", "mdi:gas-cylinder", None, "Lambda Sensor"],
    "B_FotV": ["kOhm", "mdi:fire", None, "Fire Sensor"],
    "B_cm2k": [None, "mdi:state-machine", None, "CM2K Status"],
    "B_P1": [None, "mdi:pump", None, "Boiler Pump"],
    "B_zahP1": [None, "mdi:pump", None, "Boiler Pump Demand"],
    "B_P2": [None, "mdi:pump", None, "Second Pump"],
    "B_zahP2": [None, "mdi:pump", None, "Second Pump Demand"],
    "B_P3": [None, "mdi:pump", None, "Third Pump"],
    "B_zahP3": [None, "mdi:pump", None, "Third Pump Demand"],
    "B_priS": [PERCENTAGE, "mdi:air-filter", None, "Air Flow Engine Primary"],
    "B_secS": [PERCENTAGE, "mdi:air-filter", None, "Air Flow Engine Secondary"],
    "B_zar": [None, "mdi:campfire", None, "Glow"],
    "B_zlj": [None, "mdi:book-open", None, "Operation Mode"],
    "B_gri": [None, "mdi:fire-circle", None, "Electric Heater"],
    "B_puz": [None, "mdi:transfer-up", None, "Pellet Transporter"],
    "B_doz": [None, "mdi:transfer-up", None, "Pellet Dispenzer"],
    "B_pbs": [None, "mdi:pine-tree", None, "Wood Pellet Mode"],
    "B_scs": [None, "mdi:controller-classic", None, "Control Mode"],
    "B_preuz": [None, "mdi:abacus", None, "Take Over"],
    # --- Counters (cumulative) ---
    "CNT_0": [_MIN, "mdi:timer", None, "Operation Wood"],
    "CNT_1": [_MIN, "mdi:timer", None, "Operation Pellets"],
    "CNT_2": [_MIN, "mdi:timer", None, "Pellets D6"],
    "CNT_3": [_MIN, "mdi:timer", None, "Pellets D5"],
    "CNT_4": [_MIN, "mdi:timer", None, "Pellets D4"],
    "CNT_5": [_MIN, "mdi:timer", None, "Pellets D3"],
    "CNT_6": [_MIN, "mdi:timer", None, "Pellets D2"],
    "CNT_7": [None, "mdi:counter", None, "Startup Wood"],
    "CNT_8": [None, "mdi:counter", None, "Startup Pellets"],
    "CNT_9": [_MIN, "mdi:timer", None, "DHW And Heating Time"],
    "CNT_10": [_MIN, "mdi:timer", None, "DHW Only Time"],
    "CNT_11": [_MIN, "mdi:timer", None, "Fan Time"],
    "CNT_12": [_MIN, "mdi:timer", None, "Heater Time"],
    "CNT_13": [None, "mdi:counter", None, "Heater Start"],
    "CNT_14": [_MIN, "mdi:timer", None, "Screw Feeder Time"],
    "CNT_15": [None, "mdi:counter", None, "Grate Cleaning"],
    # --- Identity / state (diagnostic, disabled by default) ---
    "B_STATE": [None, "mdi:fire", None, "Boiler State"],
    "B_VER": [None, "mdi:chip", None, "Firmware Version"],
    "B_WifiVER": [None, "mdi:chip", None, "WiFi-Box Firmware"],
    "B_PRODNAME": [None, "mdi:tag", None, "Product Name"],
    "B_BRAND": [None, "mdi:tag", None, "Brand"],
    "B_sng": [None, "mdi:lightning-bolt", None, "Power Rating"],
    "B_KONF": [None, "mdi:cog", None, "Configuration"],
    "B_INST": [None, "mdi:cog", None, "Installation Type"],
    # --- Heating circuit 1 ---
    "C1B_Tpol1": [_C, "mdi:thermometer", _TEMP, "Circuit 1 Flow Temperature"],
    "C1B_Tsob1": [_C, "mdi:thermometer", _TEMP, "Circuit 1 Room Temperature"],
    "C1B_Tpol": [_C, "mdi:thermometer", _TEMP, "Circuit 1 Flow Setpoint"],
    "C1B_Tsob": [_C, "mdi:thermometer", _TEMP, "Circuit 1 Room Setpoint"],
    "C1B_P": [None, "mdi:pump", None, "Circuit 1 Pump"],
    "C1B_onOff": [None, "mdi:toggle-switch", None, "Circuit 1 On/Off"],
    "C1B_dayNight": [None, "mdi:theme-light-dark", None, "Circuit 1 Day/Night"],
    "C1B_kor": [None, "mdi:tune", None, "Circuit 1 Correction"],
}

# Codes that are diagnostic/identity and should be disabled in the registry by default.
DIAGNOSTIC_CODES = {
    "B_STATE", "B_VER", "B_WifiVER", "B_PRODNAME", "B_BRAND",
    "B_sng", "B_KONF", "B_INST",
}
