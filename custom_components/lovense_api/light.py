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
        # Parse toys string if needed
        import json
        try:
            toys = json.loads(toys)
        except (json.JSONDecodeError, TypeError):
            toys = {}
    
    for toy_id, toy_info in toys.items():
        entities.append(LovenseLight(coordinator, toy_id, toy_info))
    
    if entities:
        async_add_entities(entities, True)


class LovenseLight(CoordinatorEntity, LightEntity):
    """Representation of a Lovense device as a light entity."""

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
            and self.coordinator.data.get("status") == "connected"
            and self._toy_info.get("connected", False)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness or 255)
        effect = kwargs.get(ATTR_EFFECT)
        
        # Convert brightness (0-255) to Lovense intensity (0-20)
        intensity = max(1, round((brightness / 255) * VIBRATE_MAX))
        
        try:
            if effect and effect in EFFECTS:
                # Use preset effect
                await self.coordinator.send_command_local(
                    command="Preset",
                    name=effect,
                    timeSec=0,  # Indefinite
                    toy=self._toy_id,
                )
                self._attr_effect = effect
            else:
                # Use vibration command
                await self.coordinator.send_command_local(
                    command=CMD_FUNCTION,
                    action=f"{ACTION_VIBRATE}:{intensity}",
                    timeSec=0,  # Indefinite
                    toy=self._toy_id,
                )
                self._attr_effect = None
            
            self._attr_is_on = True
            self._attr_brightness = brightness
            self.async_write_ha_state()
            
        except Exception as err:
            _LOGGER.error("Failed to turn on %s: %s", self._attr_name, err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        try:
            await self.coordinator.send_command_local(
                command=CMD_FUNCTION,
                action="Stop",
                timeSec=0,
                toy=self._toy_id,
            )
            
            self._attr_is_on = False
            self._attr_brightness = 0
            self._attr_effect = None
            self.async_write_ha_state()
            
        except Exception as err:
            _LOGGER.error("Failed to turn off %s: %s", self._attr_name, err)

    async def async_update(self) -> None:
        """Update the entity."""
        # Entity state is managed by coordinator
        pass
