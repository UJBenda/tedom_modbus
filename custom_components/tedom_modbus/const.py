"""Konstanty pro integraci Tedom Modbus."""

DOMAIN = "tedom_modbus"
DEFAULT_NAME = "Tedom CHP"
DEFAULT_SCAN_INTERVAL = 15
DEFAULT_PORT = 502
DEFAULT_PLUGIN = "plugin_tedom_intelicompact"
CONF_PLUGIN = "plugin"
CONF_SCAN_INTERVAL = "scan_interval"

# Zde mapujeme: "Název souboru bez .py" -> "Název v menu"
AVAILABLE_PLUGINS = {
    "plugin_tedom_intelicompact": "Tedom InteliCompact (584-generator)",
    # "plugin_tedom_iny_typ": "Tedom Jiný Typ (User Table XY)",
}
