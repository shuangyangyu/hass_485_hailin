"""Config flow for Hailin Modbus integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .tcp_client import TCPService

CONF_ENABLE_POLLING = "enable_polling"
DOMAIN = "hailin_modbus"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hailin Modbus."""

    VERSION = 1
    
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            try:
                tcp_service = TCPService(user_input[CONF_HOST], user_input[CONF_PORT])
                result = await self.hass.async_add_executor_job(tcp_service.connect)
                if not result:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title="Hailin Environmental Monitor", 
                        data=user_input
                    )
            except Exception:
                errors["base"] = "unknown"

        data_schema = vol.Schema({
            vol.Required(CONF_HOST): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT
                )
            ),
            vol.Required(CONF_PORT, default=502): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=65535,
                    mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required(CONF_ENABLE_POLLING, default=False): selector.BooleanSelector(),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )
