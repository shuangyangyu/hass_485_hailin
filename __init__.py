"""The Hailin Modbus integration."""
import os
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "hailin_modbus"

async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the Hailin Modbus component."""
    # 注册静态文件服务，用于提供图标
    integration_dir = os.path.dirname(__file__)
    hass.http.register_static_path(
        f"/local/{DOMAIN}",
        integration_dir,
        cache_headers=True,
    )
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Hailin Modbus from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    return await hass.config_entries.async_forward_entry_unload(entry, "sensor")
