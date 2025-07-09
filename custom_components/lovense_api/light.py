"""Light platform for Lovense API integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ACTION_VIBRATE,
    CMD_FUNCTION,
    DOMAIN,
    VIBRATE_MAX,
    VIBRATE_MIN,
)
from .coordinator import LovenseCoordinator

_LOGGER = logging.getLogger(__name__)

# Predefined effects
EFFECTS = ["pulse", "wave", "fireworks", "earthquake"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lovense light platform."""
    coordinator: LovenseCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Create light entities for each connected toy
    toys = coordinator.data.get("toys", {})
    if isinstance(toys, str):
        # Parse toys string if needed (from GetToys response)
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
            
        # Main vibration light for all devices
        entities.append(LovenseVibrationLight(coordinator, toy_id, toy_info))
        
        # For Solace Pro, add stroke position lights for voice control
        toy_type = toy_info.get("toyType", "").lower()
        toy_name = toy_info.get("name", "").lower()
        if "solace" in toy_type or "solace" in toy_name or "position" in str(toy_info.get("fullFunctionNames", [])).lower():
            entities.append(LovenseStrokeTopLight(coordinator, toy_id, toy_info))
            entities.append(LovenseStrokeBottomLight(coordinator, toy_id, toy_info))
    
    if entities:
        async_add_entities(entities, True)


class LovenseVibrationLight(CoordinatorEntity, LightEntity):
    """Representation of a Lovense device vibration as a light entity."""

    def __init__(
        self,
        coordinator: LovenseCoordinator,
        toy_id: str,
        toy_info: dict[str, Any],
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._toy_id = toy_id
        self._toy_info = toy_info
        self._attr_is_on = False
        self._attr_brightness = 0
        self._attr_effect = None
        
        # Device info
        self._attr_name = f"{toy_info.get('name', 'Lovense Device')} Vibration"
        self._attr_unique_id = f"{DOMAIN}_{toy_id}_vibration"
        
        # Light capabilities
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_features = LightEntityFeature.EFFECT
        self._attr_effect_list = EFFECTS
        
        # Brightness range (0-255 maps to 0-20 Lovense range)
        self._attr_min_brightness = 1
        self._attr_max_brightness = 255

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness or 255)
        effect = kwargs.get(ATTR_EFFECT)
        
        # Convert brightness (0-255) to Lovense intensity (0-20)
        intensity = max(1, round((brightness / 255) * VIBRATE_MAX))
        
        # Update state immediately for instant response
        self._attr_is_on = True
        self._attr_brightness = brightness
        if effect and effect in EFFECTS:
            self._attr_effect = effect
        else:
            self._attr_effect = None
        self.async_write_ha_state()
        
        try:
            if effect and effect in EFFECTS:
                # Use preset effect
                await self.coordinator.send_command_local(
                    command="Preset",
                    name=effect,
                    timeSec=0,  # Indefinite
                    toy=self._toy_id,
                )
            else:
                # Use unified command system to preserve stroke settings
                await self.coordinator.send_unified_command(
                    self._toy_id,
                    vibration=intensity
                )
            
        except Exception as err:
            _LOGGER.error("Failed to turn on %s: %s", self._attr_name, err)
            # Revert state on error
            self._attr_is_on = False
            self._attr_brightness = 0
            self._attr_effect = None
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        # Update state immediately for instant response
        self._attr_is_on = False
        self._attr_brightness = 0
        self._attr_effect = None
        self.async_write_ha_state()
        
        try:
            # Use unified command system to stop vibration but preserve stroke settings
            await self.coordinator.send_unified_command(
                self._toy_id,
                vibration=0
            )
            
        except Exception as err:
            _LOGGER.error("Failed to turn off %s: %s", self._attr_name, err)
            # Revert state on error
            self._attr_is_on = True
            self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        # Entity state is managed by coordinator
        pass


class LovenseStrokeTopLight(CoordinatorEntity, LightEntity):
    """Representation of Solace Pro stroke top position as a light entity for voice control."""

    def __init__(
        self,
        coordinator: LovenseCoordinator,
        toy_id: str,
        toy_info: dict[str, Any],
    ) -> None:
        """Initialize the stroke top light."""
        super().__init__(coordinator)
        self._toy_id = toy_id
        self._toy_info = toy_info
        self._attr_is_on = False
        self._attr_brightness = 0  # Default to 0% brightness = position 100 (top)
        
        # Device info
        self._attr_name = f"{toy_info.get('name', 'Lovense Device')} Stroke Top Limit"
        self._attr_unique_id = f"{DOMAIN}_{toy_id}_stroke_top_limit"
        
        # Light capabilities
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        
        # Brightness range (0-255 maps to 0-100 position)
        self._attr_min_brightness = 1
        self._attr_max_brightness = 255

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set the stroke top limit."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness or 255)
        
        # Convert brightness (0-255) to position (0-100) - INVERTED for intuitive GUI
        # 0% brightness = position 100 (top), 100% brightness = position 0 (bottom)
        position = 100 - round((brightness / 255) * 100)
        
        # Update state immediately for instant response
        self._attr_is_on = True
        self._attr_brightness = brightness
        self.async_write_ha_state()
        
        try:
            # Store the top limit position persistently
            if not hasattr(self.coordinator, 'stroke_positions'):
                self.coordinator.stroke_positions = {}
            if self._toy_id not in self.coordinator.stroke_positions:
                self.coordinator.stroke_positions[self._toy_id] = {'top': 100, 'bottom': 0}
            
            self.coordinator.stroke_positions[self._toy_id]['top'] = position
            
            # Create stroke range and use unified command system
            bottom_limit = self.coordinator.stroke_positions[self._toy_id]['bottom']
            stroke_range = f"{bottom_limit}-{position}"
            
            await self.coordinator.send_unified_command(
                self._toy_id,
                stroke_range=stroke_range
            )
            
            _LOGGER.debug("Set stroke top limit to %s (range: %s)", position, stroke_range)
            
        except Exception as err:
            _LOGGER.error("Failed to set stroke top limit for %s: %s", self._attr_name, err)
            # Revert state on error
            self._attr_is_on = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off stroke (stop movement)."""
        # Update state immediately for instant response
        self._attr_is_on = False
        self._attr_brightness = 0
        self.async_write_ha_state()
        
        try:
            # Use unified command system to stop stroke but preserve vibration
            await self.coordinator.send_unified_command(
                self._toy_id,
                stroke_range=None  # Clear stroke range
            )
            
        except Exception as err:
            _LOGGER.error("Failed to stop stroke for %s: %s", self._attr_name, err)
            # Revert state on error
            self._attr_is_on = True
            self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        pass


class LovenseStrokeBottomLight(CoordinatorEntity, LightEntity):
    """Representation of Solace Pro stroke bottom position as a light entity for voice control."""

    def __init__(
        self,
        coordinator: LovenseCoordinator,
        toy_id: str,
        toy_info: dict[str, Any],
    ) -> None:
        """Initialize the stroke bottom light."""
        super().__init__(coordinator)
        self._toy_id = toy_id
        self._toy_info = toy_info
        self._attr_is_on = False
        self._attr_brightness = 255  # Default to 100% brightness = position 0 (bottom)
        
        # Device info
        self._attr_name = f"{toy_info.get('name', 'Lovense Device')} Stroke Bottom Limit"
        self._attr_unique_id = f"{DOMAIN}_{toy_id}_stroke_bottom_limit"
        
        # Light capabilities
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        
        # Brightness range (0-255 maps to 0-100 position)
        self._attr_min_brightness = 1
        self._attr_max_brightness = 255

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set the stroke bottom limit."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness or 1)
        
        # Convert brightness (0-255) to position (0-100) - INVERTED for intuitive GUI
        # 0% brightness = position 100 (top), 100% brightness = position 0 (bottom)
        position = 100 - round((brightness / 255) * 100)
        
        # Update state immediately for instant response
        self._attr_is_on = True
        self._attr_brightness = brightness
        self.async_write_ha_state()
        
        try:
            # Store the bottom limit position persistently
            if not hasattr(self.coordinator, 'stroke_positions'):
                self.coordinator.stroke_positions = {}
            if self._toy_id not in self.coordinator.stroke_positions:
                self.coordinator.stroke_positions[self._toy_id] = {'top': 100, 'bottom': 0}
            
            self.coordinator.stroke_positions[self._toy_id]['bottom'] = position
            
            # Create stroke range and use unified command system
            top_limit = self.coordinator.stroke_positions[self._toy_id]['top']
            stroke_range = f"{position}-{top_limit}"
            
            await self.coordinator.send_unified_command(
                self._toy_id,
                stroke_range=stroke_range
            )
            
            _LOGGER.debug("Set stroke bottom limit to %s (range: %s)", position, stroke_range)
            
        except Exception as err:
            _LOGGER.error("Failed to set stroke bottom limit for %s: %s", self._attr_name, err)
            # Revert state on error
            self._attr_is_on = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off stroke (stop movement)."""
        # Update state immediately for instant response
        self._attr_is_on = False
        self._attr_brightness = 0
        self.async_write_ha_state()
        
        try:
            # Use unified command system to stop stroke but preserve vibration
            await self.coordinator.send_unified_command(
                self._toy_id,
                stroke_range=None  # Clear stroke range
            )
            
        except Exception as err:
            _LOGGER.error("Failed to stop stroke for %s: %s", self._attr_name, err)
            # Revert state on error
            self._attr_is_on = True
            self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        pass
