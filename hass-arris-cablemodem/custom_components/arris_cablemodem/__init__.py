"""ARRIS Surfboard Cable Modem Integration."""
from __future__ import annotations

import logging
from datetime import timedelta

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .modem import ArrisModem

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the ARRIS SB6183 component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ARRIS SB6183 from a config entry."""
    host = entry.data["host"]
    
    modem = ArrisModem(host)
    
    async def async_update_data():
        """Fetch data from modem."""
        try:
            async with async_timeout.timeout(10):
                return await hass.async_add_executor_job(modem.get_status)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with modem: {err}") from err
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="arris_sb6183",
        update_method=async_update_data,
        update_interval=timedelta(seconds=60),
    )
    
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
