"""Konstanty pro integraci Tedom Modbus."""

DOMAIN = "tedom_modbus"
DEFAULT_NAME = "Tedom CHP"
DEFAULT_SCAN_INTERVAL = 15
DEFAULT_PORT = 502
CONF_PLUGIN = "plugin"

# Zde mapujeme: "Název v menu" -> "Název souboru bez .py"
AVAILABLE_PLUGINS = {
    "plugin_tedom_intelicompact": "Tedom InteliCompact (User Table 117)",
    # "tedom_iny_typ": "Tedom Jiný Typ (User Table XY)",
}
