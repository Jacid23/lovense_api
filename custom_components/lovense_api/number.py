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
    CMD_POSITION,
    DOMAIN,
    POSITION_MAX,
    POSITION_MIN,
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
        # Only create position control for devices that support it (like Solace Pro)
        toy_type = toy_info.get("toyType", "").lower()
        if "solace" in toy_type or "position" in str(toy_info.get("fullFunctionNames", [])).lower():
            entities.append(LovensePositionNumber(coordinator, toy_id, toy_info))
    
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
            and self.coordinator.data.get("status") == "connected"
            and self._toy_info.get("connected", False)
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the position value."""
        try:
            await self.coordinator.send_command_local(
                command=CMD_POSITION,
                value=str(int(value)),
                toy=self._toy_id,
            )
            
            self._attr_native_value = value
            self.async_write_ha_state()
            
        except Exception as err:
            _LOGGER.error("Failed to set position for %s: %s", self._attr_name, err)

    async def async_update(self) -> None:
        """Update the entity."""
        # Entity state is managed by coordinator
        pass
