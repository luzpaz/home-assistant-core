"""Number platform for Plugwise integration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from plugwise import Smile

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PlugwiseDataUpdateCoordinator
from .entity import PlugwiseEntity


@dataclass
class PlugwiseEntityDescriptionMixin:
    """Mixin values for Plugwse entities."""

    command: Callable[[Smile, float], Awaitable[None]]


@dataclass
class PlugwiseNumberEntityDescription(
    NumberEntityDescription, PlugwiseEntityDescriptionMixin
):
    """Class describing Plugwise Number entities."""


NUMBER_TYPES = (
    PlugwiseNumberEntityDescription(
        key="maximum_boiler_temperature",
        command=lambda api, value: api.set_max_boiler_temperature(value),
        device_class=NumberDeviceClass.TEMPERATURE,
        name="Maximum Boiler Temperature Setpoint",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Plugwise number platform."""

    coordinator: PlugwiseDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    entities: list[PlugwiseNumberEntity] = []
    for device_id, device in coordinator.data.devices.items():
        for description in NUMBER_TYPES:
            if description.key in device:
                entities.append(
                    PlugwiseNumberEntity(coordinator, device_id, description)
                )

    async_add_entities(entities)


class PlugwiseNumberEntity(PlugwiseEntity, NumberEntity):
    """Representation of a Plugwise number."""

    entity_description: PlugwiseNumberEntityDescription

    def __init__(
        self,
        coordinator: PlugwiseDataUpdateCoordinator,
        device_id: str,
        description: PlugwiseNumberEntityDescription,
    ) -> None:
        """Initiate Plugwise Number."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}-{description.key}"
        self._attr_name = (f"{self.device['name']} {description.name}").lstrip()
        self._attr_mode = NumberMode.BOX

    @property
    def native_step(self) -> float:
        """Return the setpoint step value."""
        return max(self.device["resolution"], 1)

    @property
    def native_value(self) -> float:
        """Return the present setpoint value."""
        return self.device[self.entity_description.key]

    @property
    def native_min_value(self) -> float:
        """Return the setpoint min. value."""
        return self.device["lower_bound"]

    @property
    def native_max_value(self) -> float:
        """Return the setpoint max. value."""
        return self.device["upper_bound"]

    async def async_set_native_value(self, value: float) -> None:
        """Change to the new setpoint value."""
        await self.entity_description.command(self.coordinator.api, value)
        await self.coordinator.async_request_refresh()
