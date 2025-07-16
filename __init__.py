"""The Hailin Modbus integration."""
from __future__ import annotations

import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.http import StaticPathConfig

DOMAIN = "hailin_modbus"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hailin Modbus component."""
    # Register static file paths for icon access.
    integration_dir = os.path.dirname(__file__)
    brands_dir = os.path.join(integration_dir, "brands")
    
    await hass.http.async_register_static_paths([
        StaticPathConfig(f"/local/{DOMAIN}", integration_dir, True),
        StaticPathConfig(f"/local/{DOMAIN}/brands", brands_dir, True)
    ])
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hailin Modbus from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_forward_entry_unload(entry, "sensor")
