"""Support for Healthchecksio sensors."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HealtchecksioCoordinator
from .const import DOMAIN, ICON_MAPPING

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up check sensor platform."""
    name: str = entry.title
    coordinator: HealtchecksioCoordinator = hass.data[DOMAIN][entry.entry_id]
    check_id: str = entry.data[CONF_UNIQUE_ID]

    async_add_entities([CheckSensor(coordinator, name, check_id)], False)


class CheckSensor(CoordinatorEntity, SensorEntity):
    """The sensor entity for a check."""

    def __init__(
        self, coordinator: HealtchecksioCoordinator, name: str, check_id: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

        self._attr_name = name
        self._attr_should_poll = True
        self._attr_unique_id = check_id
        self._attr_extra_state_attributes = {}
        self._icon = ICON_MAPPING["up"]

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self):
        """Fetch data and update the entity."""
        self._attr_native_value = self.coordinator.data[
            self.unique_id
        ].status.capitalize()
        self._icon = ICON_MAPPING[self.coordinator.data[self.unique_id].status]
        self._attr_extra_state_attributes.update(
            {
                "name": self.coordinator.data[self.unique_id].name,
                "description": self.coordinator.data[self.unique_id].desc,
                "tags": self.coordinator.data[self.unique_id].tags,
                "schedule": self.coordinator.data[self.unique_id].schedule,
            }
        )

        self.async_write_ha_state()
