from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
from .plugin_tedom import TedomPlugin

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Registrace přepínačů (Select) pro danou instanci Tedomu."""
    hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    
    # Ověříme, zda plugin definuje nějaké přepínače
    if hasattr(hub.plugin, "SELECT_TYPES"):
        entities = [TedomSelect(hub, desc) for desc in hub.plugin.SELECT_TYPES]
        async_add_entities(entities)
        
        # Přidáme entity do seznamu v Hubu pro aktualizaci stavu
        hub.entities.extend(entities)

class TedomSelect(SelectEntity):
    """Reprezentace přepínače režimu (Read/Write) přes Modbus."""

    _attr_has_entity_name = True # Moderní seskupování pod zařízení

    def __init__(self, hub, description):
        """Inicializace přepínače."""
        self._hub = hub
        self.entity_description = description
        
        # Unikátní ID pro HA
        self._attr_unique_id = f"{hub._name}_{description.key}".lower()
        
        # Název entity (HA k němu přidá název zařízení sám)
        self._attr_name = description.name
        
        # Načtení dostupných textových voleb z mapy (např. VYP, SEM, AUT)
        self._attr_options = list(description.options_map.keys())
        
        # Vypneme polling, Hub data posílá hromadně
        self._attr_should_poll = False 

    @property
    def device_info(self) -> DeviceInfo:
        """Informace o zařízení pro UI."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._hub._name)},
            name=self._hub._name,
            manufacturer="Tedom",
            model=TedomPlugin.NAME,
        )

    @property
    def current_option(self):
        """Vrátí aktuálně vybraný textový režim na základě čísla v Modbusu."""
        # Získáme aktuální hodnotu z mezipaměti Hubu
        val = self._hub.data.get(self.entity_description.key)
        
        if val is not None:
            # Najdeme odpovídající text v options_map
            for name, v in self.entity_description.options_map.items():
                if int(v) == int(val):
                    return name
        return None

    async def async_select_option(self, option: str) -> None:
        """Změna režimu stroje uživatelem z UI."""
        # Najdeme číselnou hodnotu pro vybraný text
        val_to_write = self.entity_description.options_map[option]
        
        # Zapíšeme do registru a automaticky uvolníme slot (díky úpravě v Hubu)
        await self._hub.async_write_register(
            address=self.entity_description.address, 
            value=val_to_write
        )