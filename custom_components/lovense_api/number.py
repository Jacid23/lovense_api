"""Number platform for Lovense API integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CMD_FUNCTION,
    CMD_POSITION,
    DOMAIN,
    POSITION_MAX,
    POSITION_MIN,
    TRAVEL_MAX,
    TRAVEL_MIN,
)
from .coordinator import LovenseCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lovense number platform."""
    coordinator: LovenseCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Create number entities for position control (Solace Pro)
    toys = coordinator.data.get("toys", {})
    if isinstance(toys, str):
        # Parse toys string if needed
        import json
        try:
            toys = json.loads(toys)
        except (json.JSONDecodeError, TypeError):
            toys = {}
    
    for toy_id, toy_info in toys.items():
        # Ensure toy_info is a dict (handle both callback and API formats)
        if isinstance(toy_info, str):
            # If toy_info is just an ID string, create minimal info
            toy_info = {"id": toy_info, "name": "Lovense Device", "status": 1}
        elif not isinstance(toy_info, dict):
            # Skip if toy_info is not valid
            continue
            
        # Only create controls for devices that support it (like Solace Pro)
        toy_type = toy_info.get("toyType", "").lower()
        toy_name = toy_info.get("name", "").lower()
        if "solace" in toy_type or "solace" in toy_name or "position" in str(toy_info.get("fullFunctionNames", [])).lower():
            # Position control (where the stroker is positioned)
            entities.append(LovensePositionNumber(coordinator, toy_id, toy_info))
            # Stroke range controls (top and bottom positions like in the app)
            entities.append(LovenseStrokeTopNumber(coordinator, toy_id, toy_info))
            entities.append(LovenseStrokeBottomNumber(coordinator, toy_id, toy_info))
    
    if entities:
        async_add_entities(entities, True)


class LovensePositionNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Lovense device position control."""

    def __init__(
        self,
        coordinator: LovenseCoordinator,
        toy_id: str,
        toy_info: dict[str, Any],
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._toy_id = toy_id
        self._toy_info = toy_info
        
        # Device info
        self._attr_name = f"{toy_info.get('name', 'Lovense Device')} Position"
        self._attr_unique_id = f"{DOMAIN}_{toy_id}_position"
        
        # Number configuration
        self._attr_native_min_value = POSITION_MIN
        self._attr_native_max_value = POSITION_MAX
        self._attr_native_step = 1
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = "mdi:arrow-up-down"
        
        # Current value
        self._attr_native_value = 0

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
            and self.coordinator.data.get("toys", {})
            and self._toy_id in self.coordinator.data.get("toys", {})
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the position value."""
        # Update state immediately for instant response
        self._attr_native_value = value
        self.async_write_ha_state()
        
        try:
            # Use unified command system to preserve other settings
            await self.coordinator.send_unified_command(
                self._toy_id,
                position=value
            )
            
        except Exception as err:
            _LOGGER.error("Failed to set position for %s: %s", self._attr_name, err)
            # Could revert state on error if needed
            # self._attr_native_value = previous_value
            # self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        # Entity state is managed by coordinator
        pass


class LovenseStrokeTopNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Lovense device stroke top position control."""

    def __init__(
        self,
        coordinator: LovenseCoordinator,
        toy_id: str,
        toy_info: dict[str, Any],
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._toy_id = toy_id
        self._toy_info = toy_info
        
        # Device info
        device_name = toy_info.get("name", "Lovense Device").title()
        self._attr_name = f"{device_name} Stroke Top"
        self._attr_unique_id = f"{DOMAIN}_{toy_id}_stroke_top"
        
        # Number configuration
        self._attr_native_min_value = POSITION_MIN
        self._attr_native_max_value = POSITION_MAX
        self._attr_native_step = 1
        self._attr_native_value = 75  # Default top position
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = "mdi:arrow-up"
        self._attr_entity_description = "Top position of stroke range (upper limit)"

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
            and self.coordinator.data.get("toys", {})
            and self._toy_id in self.coordinator.data.get("toys", {})
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the stroke top position."""
        # Update state immediately for instant response
        self._attr_native_value = value
        self.async_write_ha_state()
        
        try:
            # Get the current bottom position or use default
            bottom_entities = [
                entity for entity in self.coordinator.hass.data[DOMAIN].values()
                if hasattr(entity, '_attr_unique_id') and 
                entity._attr_unique_id == f"{DOMAIN}_{self._toy_id}_stroke_bottom"
            ]
            bottom_value = bottom_entities[0]._attr_native_value if bottom_entities else 25
            
            # Ensure top is above bottom
            if value <= bottom_value:
                value = bottom_value + 1
                self._attr_native_value = value
                self.async_write_ha_state()
            
            # Set stroke range using unified command system
            stroke_range = f"{int(bottom_value)}-{int(value)}"
            await self.coordinator.send_unified_command(
                self._toy_id,
                stroke_range=stroke_range
            )
            
            _LOGGER.debug("Set stroke top %s to %s (range: %s)", 
                         self._attr_name, value, stroke_range)
            
        except Exception as err:
            _LOGGER.error("Failed to set stroke top for %s: %s", self._attr_name, err)

    async def async_update(self) -> None:
        """Update the entity."""
        pass


class LovenseStrokeBottomNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Lovense device stroke bottom position control."""

    def __init__(
        self,
        coordinator: LovenseCoordinator,
        toy_id: str,
        toy_info: dict[str, Any],
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._toy_id = toy_id
        self._toy_info = toy_info
        
        # Device info
        device_name = toy_info.get("name", "Lovense Device").title()
        self._attr_name = f"{device_name} Stroke Bottom"
        self._attr_unique_id = f"{DOMAIN}_{toy_id}_stroke_bottom"
        
        # Number configuration
        self._attr_native_min_value = POSITION_MIN
        self._attr_native_max_value = POSITION_MAX
        self._attr_native_step = 1
        self._attr_native_value = 25  # Default bottom position
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = "mdi:arrow-down"
        self._attr_entity_description = "Bottom position of stroke range (lower limit)"

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
            and self.coordinator.data.get("toys", {})
            and self._toy_id in self.coordinator.data.get("toys", {})
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the stroke bottom position."""
        # Update state immediately for instant response
        self._attr_native_value = value
        self.async_write_ha_state()
        
        try:
            # Get the current top position or use default
            top_entities = [
                entity for entity in self.coordinator.hass.data[DOMAIN].values()
                if hasattr(entity, '_attr_unique_id') and 
                entity._attr_unique_id == f"{DOMAIN}_{self._toy_id}_stroke_top"
            ]
            top_value = top_entities[0]._attr_native_value if top_entities else 75
            
            # Ensure bottom is below top
            if value >= top_value:
                value = top_value - 1
                self._attr_native_value = value
                self.async_write_ha_state()
            
            # Set stroke range using unified command system
            stroke_range = f"{int(value)}-{int(top_value)}"
            await self.coordinator.send_unified_command(
                self._toy_id,
                stroke_range=stroke_range
            )
            
            _LOGGER.debug("Set stroke bottom %s to %s (range: %s)", 
                         self._attr_name, value, stroke_range)
            
        except Exception as err:
            _LOGGER.error("Failed to set stroke bottom for %s: %s", self._attr_name, err)

    async def async_update(self) -> None:
        """Update the entity."""
        pass
