"""Config flow for ARRIS Surfoard Cable Modems with auto-discovery."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import DEFAULT_HOST, DISCOVERY_HOSTS, DOMAIN, SUPPORTED_MODELS
from .modem import ArrisModem

_LOGGER = logging.getLogger(__name__)


class ArrisSB6183ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ARRIS SB6183."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._discovered_modems = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - try auto-discovery first."""
        if user_input is None:
            # Try to discover modems
            discovered = await self._async_discover_modems()
            
            if discovered:
                # Show discovered modems
                self._discovered_modems = discovered
                return await self.async_step_discovery()
            else:
                # No modems found, show manual entry
                return await self.async_step_manual()
        
        return await self.async_step_manual(user_input)

    async def async_step_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle discovery step - let user pick from discovered modems."""
        if user_input is not None:
            selected = user_input["modem"]
            for modem_info in self._discovered_modems:
                if modem_info["display"] == selected:
                    return await self._async_create_entry(
                        modem_info["host"], modem_info["model"]
                    )
        
        # Build options for selection
        modem_options = {m["display"]: m["display"] for m in self._discovered_modems}
        modem_options["manual"] = "Enter IP manually"
        
        return self.async_show_form(
            step_id="discovery",
            data_schema=vol.Schema(
                {
                    vol.Required("modem"): vol.In(modem_options),
                }
            ),
            description_placeholders={
                "found_count": str(len(self._discovered_modems))
            },
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual IP entry."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            
            # Test connection
            modem = ArrisModem(host)
            try:
                status = await self.hass.async_add_executor_job(modem.get_status)
                model = status.get("model", "Unknown")
                return await self._async_create_entry(host, model)
            except Exception as err:
                _LOGGER.error("Cannot connect to modem at %s: %s", host, err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                }
            ),
            errors=errors,
        )

    async def _async_discover_modems(self) -> list[dict]:
        """Attempt to discover ARRIS modems on the network."""
        discovered = []
        
        for host in DISCOVERY_HOSTS:
            try:
                modem = ArrisModem(host)
                status = await self.hass.async_add_executor_job(modem.get_status)
                
                # Check if it's a supported model
                model = status.get("model", "")
                if any(supported in model for supported in SUPPORTED_MODELS):
                    discovered.append({
                        "host": host,
                        "model": model,
                        "display": f"{model} at {host}",
                    })
                    _LOGGER.info("Discovered ARRIS modem: %s at %s", model, host)
            except Exception as err:
                _LOGGER.debug("No modem found at %s: %s", host, err)
                continue
        
        return discovered

    async def _async_create_entry(self, host: str, model: str) -> FlowResult:
        """Create the config entry."""
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()
        
        return self.async_create_entry(
            title=f"{model} ({host})",
            data={CONF_HOST: host},
        )

