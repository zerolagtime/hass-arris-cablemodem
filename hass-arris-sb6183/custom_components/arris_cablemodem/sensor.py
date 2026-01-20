"""Sensor platform for ARRIS Surfboard Cable Modems."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, UnitOfFrequency
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


@dataclass
class ArrisSensorEntityDescription(SensorEntityDescription):
    """Describe ARRIS sensor entity."""

    value_fn: Callable[[dict], any] = None


SENSOR_TYPES: tuple[ArrisSensorEntityDescription, ...] = (
    ArrisSensorEntityDescription(
        key="connectivity",
        name="Connectivity State",
        icon="mdi:check-network",
        value_fn=lambda data: data.get("startup", {}).get("connectivity"),
    ),
    ArrisSensorEntityDescription(
        key="boot",
        name="Boot State",
        icon="mdi:power",
        value_fn=lambda data: data.get("startup", {}).get("boot"),
    ),
    ArrisSensorEntityDescription(
        key="security",
        name="Security",
        icon="mdi:shield-check",
        value_fn=lambda data: data.get("startup", {}).get("security"),
    ),
    ArrisSensorEntityDescription(
        key="ds_channels",
        name="Downstream Channels",
        icon="mdi:download-network",
        value_fn=lambda data: len(data.get("downstream", [])),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ArrisSensorEntityDescription(
        key="us_channels",
        name="Upstream Channels",
        icon="mdi:upload-network",
        value_fn=lambda data: len(data.get("upstream", [])),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ArrisSensorEntityDescription(
        key="ds_avg_power",
        name="Downstream Average Power",
        icon="mdi:signal",
        native_unit_of_measurement="dBmV",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: round(
            sum(ch["power"] for ch in data.get("downstream", [])) / len(data.get("downstream", []))
            if data.get("downstream") else None, 1
        ),
    ),
    ArrisSensorEntityDescription(
        key="ds_avg_snr",
        name="Downstream Average SNR",
        icon="mdi:signal-variant",
        native_unit_of_measurement="dB",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: round(
            sum(ch["snr"] for ch in data.get("downstream", [])) / len(data.get("downstream", []))
            if data.get("downstream") else None, 1
        ),
    ),
    ArrisSensorEntityDescription(
        key="us_avg_power",
        name="Upstream Average Power",
        icon="mdi:signal",
        native_unit_of_measurement="dBmV",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: round(
            sum(ch["power"] for ch in data.get("upstream", [])) / len(data.get("upstream", []))
            if data.get("upstream") else None, 1
        ),
    ),
    ArrisSensorEntityDescription(
        key="ds_total_corrected",
        name="Downstream Total Corrected Errors",
        icon="mdi:alert-circle",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: sum(ch["corrected"] for ch in data.get("downstream", [])),
    ),
    ArrisSensorEntityDescription(
        key="ds_total_uncorrectable",
        name="Downstream Total Uncorrectable Errors",
        icon="mdi:alert",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: sum(ch["uncorrectable"] for ch in data.get("downstream", [])),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ARRIS sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Get model from data
    model = coordinator.data.get("model", "ARRIS Modem")
    
    # Add main sensors
    for description in SENSOR_TYPES:
        entities.append(ArrisSensor(coordinator, description, entry, model))
    
    # Add per-channel sensors
    if coordinator.data:
        # Downstream channel sensors
        for channel in coordinator.data.get("downstream", []):
            ch_num = channel["channel"]
            entities.extend([
                ArrisChannelSensor(
                    coordinator,
                    ArrisSensorEntityDescription(
                        key=f"ds_ch{ch_num}_power",
                        name=f"DS Channel {ch_num} Power",
                        icon="mdi:signal",
                        native_unit_of_measurement="dBmV",
                        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                        state_class=SensorStateClass.MEASUREMENT,
                        suggested_display_precision=1,
                    ),
                    entry,
                    model,
                    "downstream",
                    ch_num,
                    "power",
                ),
                ArrisChannelSensor(
                    coordinator,
                    ArrisSensorEntityDescription(
                        key=f"ds_ch{ch_num}_snr",
                        name=f"DS Channel {ch_num} SNR",
                        icon="mdi:signal-variant",
                        native_unit_of_measurement="dB",
                        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                        state_class=SensorStateClass.MEASUREMENT,
                        suggested_display_precision=1,
                    ),
                    entry,
                    model,
                    "downstream",
                    ch_num,
                    "snr",
                ),
            ])
        
        # Upstream channel sensors
        for channel in coordinator.data.get("upstream", []):
            ch_num = channel["channel"]
            entities.append(
                ArrisChannelSensor(
                    coordinator,
                    ArrisSensorEntityDescription(
                        key=f"us_ch{ch_num}_power",
                        name=f"US Channel {ch_num} Power",
                        icon="mdi:signal",
                        native_unit_of_measurement="dBmV",
                        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                        state_class=SensorStateClass.MEASUREMENT,
                        suggested_display_precision=1,
                    ),
                    entry,
                    model,
                    "upstream",
                    ch_num,
                    "power",
                )
            )
    
    async_add_entities(entities)


class ArrisSensor(CoordinatorEntity, SensorEntity):
    """Representation of an ARRIS sensor."""

    entity_description: ArrisSensorEntityDescription

    def __init__(self, coordinator, description, entry, model):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": model,
            "manufacturer": "ARRIS",
            "model": model,
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.coordinator.data)
        return None


class ArrisChannelSensor(CoordinatorEntity, SensorEntity):
    """Representation of an ARRIS channel sensor."""

    entity_description: ArrisSensorEntityDescription

    def __init__(self, coordinator, description, entry, model, channel_type, channel_num, field):
        """Initialize the channel sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._channel_type = channel_type
        self._channel_num = channel_num
        self._field = field
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": model,
            "manufacturer": "ARRIS",
            "model": model,
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        channels = self.coordinator.data.get(self._channel_type, [])
        for channel in channels:
            if channel["channel"] == self._channel_num:
                return channel.get(self._field)
        return None

