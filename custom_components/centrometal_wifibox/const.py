"""Constants for the Centrometal WiFi-Box (local) integration."""

DOMAIN = "centrometal_wifibox"

CONF_PORT = "port"
CONF_NAME = "name"

# The box always connects to portal.centrometal.hr on TCP 1883, so on the host the
# box's DNS resolves to, the broker must listen on 1883. The port stays configurable
# only for NAT/port-forwarding setups.
DEFAULT_PORT = 1883
DEFAULT_NAME = "Centrometal WiFi-Box"

MANUFACTURER = "Centrometal"

# Dispatcher signals (suffixed with the config entry id at send/connect time).
SIGNAL_UPDATE = "centrometal_wifibox_update"
SIGNAL_NEW_KEYS = "centrometal_wifibox_new_keys"

# Prefix used for unmapped raw codes, mirroring the cloud integration convention.
UNKNOWN_PREFIX = "{?}"
