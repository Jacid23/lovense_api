"""Sensor platform for Lovense API integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LovenseCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lovense sensor platform."""
    coordinator: LovenseCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Create sensor entities for each connected toy
    toys = coordinator.data.get("toys", {})
    if isinstance(toys, str):
        # Parse toys string if needed
        import json
        try:
            toys = json.loads(toys)
        except (json.JSONDecodeError, TypeError):
            toys = {}
    
    for toy_id, toy_info in toys.items():
        # Battery sensor
        if "battery" in toy_info:
            entities.append(LovenseBatterySensor(coordinator, toy_id, toy_info))
        
        # Connection status sensor
        entities.append(LovenseStatusSensor(coordinator, toy_id, toy_info))
    
    if entities:
        async_add_entities(entities, True)


class LovenseBatterySensor(CoordinatorEntity, SensorEntity):
    """Battery sensor for Lovense device."""

    def __init__(
        self,
        coordinator: LovenseCoordinator,
        toy_id: str,
        toy_info: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._toy_id = toy_id
        self._toy_info = toy_info
        
        # Device info
        self._attr_name = f"{toy_info.get('name', 'Lovense Device')} Battery"
        self._attr_unique_id = f"{DOMAIN}_{toy_id}_battery"
        
        # Sensor configuration
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:battery"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._toy_id)},
            "name": self._toy_info.get("name", "Lovense Device"),
            "manufacturer": "Lovense",
            "model": self._toy_info.get("name", "Unknown"),
            "sw_version": self._toy_info.get("fVersion"),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get("status") == "connected"
        )

    @property
    def native_value(self) -> int | None:
        """Return the battery level."""
        toys = self.coordinator.data.get("toys", {})
        if isinstance(toys, str):
            import json
            try:
                toys = json.loads(toys)
            except (json.JSONDecodeError, TypeError):
                return None
        
        toy_info = toys.get(self._toy_id, {})
        return toy_info.get("battery")


class LovenseStatusSensor(CoordinatorEntity, SensorEntity):
    """Connection status sensor for Lovense device."""

    def __init__(
        self,
        coordinator: LovenseCoordinator,
        toy_id: str,
        toy_info: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._toy_id = toy_id
        self._toy_info = toy_info
        
        # Device info
        self._attr_name = f"{toy_info.get('name', 'Lovense Device')} Status"
        self._attr_unique_id = f"{DOMAIN}_{toy_id}_status"
        
        # Sensor configuration
        self._attr_icon = "mdi:connection"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._toy_id)},
            "name": self._toy_info.get("name", "Lovense Device"),
            "manufacturer": "Lovense",
            "model": self._toy_info.get("name", "Unknown"),
            "sw_version": self._toy_info.get("fVersion"),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get("status") == "connected"
        )

    @property
    def native_value(self) -> str:
        """Return the connection status."""
        toys = self.coordinator.data.get("toys", {})
        if isinstance(toys, str):
            import json
            try:
                toys = json.loads(toys)
            except (json.JSONDecodeError, TypeError):
                return "unknown"
        
        toy_info = toys.get(self._toy_id, {})
        connected = toy_info.get("connected", False)
        return "connected" if connected else "disconnected"
