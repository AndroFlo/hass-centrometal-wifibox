"""Constants for the Centrometal WiFi-Box (local) integration."""

DOMAIN = "centrometal_wifibox"

CONF_NAME = "name"
CONF_SERIAL = "serial"
CONF_PRODUCT = "product"
# Optional 40-hex `_sign` captured from a real cloud REFRESH, used as the replay variant.
# Left empty by default: no capture of ours is shipped with the integration.
CONF_REFRESH_SIGN = "refresh_sign"

# Boiler type as it appears in the MQTT topics (cm.inst.<product>.<serial>).
DEFAULT_PRODUCT = "biopl"
DEFAULT_NAME = "Centrometal WiFi-Box"

MANUFACTURER = "Centrometal"

# Dispatcher signals (suffixed with the config entry id at send/connect time).
SIGNAL_UPDATE = "centrometal_wifibox_update"
SIGNAL_NEW_KEYS = "centrometal_wifibox_new_keys"

# Prefix used for unmapped raw codes, mirroring the cloud integration convention.
UNKNOWN_PREFIX = "{?}"
