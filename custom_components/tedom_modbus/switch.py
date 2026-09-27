"""Entity plánovače podle spotových cen (switch)."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from . import planner_entities


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities(planner_entities.switches(hass.data[DOMAIN][entry.entry_id]["planner"]))
