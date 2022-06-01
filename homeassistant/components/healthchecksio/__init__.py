"""The healthchecksio integration."""
from __future__ import annotations

from asyncio import Lock
from datetime import timedelta
import logging

from construct import Optional
from healthchecks_io import (
    AsyncClient,
    Check,
    HCAPIAuthError,
    HCAPIError,
    HCAPIRateLimitError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, IntegrationError
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

KEY_COORDINATORS = "coordinators"
KEY_COORDINATOR_CONFIG_LOCK = "coordinator_config_lock"
PLATFORMS = [Platform.SENSOR]


class HealtchecksioCoordinator(DataUpdateCoordinator):
    """Custom coordinator."""

    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        """Initialise the instance."""
        self._api_key: str = api_key
        self._client = AsyncClient(api_key=api_key, client=get_async_client(hass))
        super().__init__(
            hass,
            _LOGGER,
            name=f"healthchecksio-{api_key}",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
            update_method=self._async_get_checks,
        )

    async def _async_get_checks(self) -> dict[str, Check]:
        """Fetch API data to get the information on all the checks for the API key."""
        try:
            checks = await self._client.get_checks()
            return {check.uuid: check for check in checks if check.uuid}
        except HCAPIAuthError as err:
            raise ConfigEntryAuthFailed from err
        except HCAPIRateLimitError as err:
            raise IntegrationError(
                "The rate limit for this API key has been reached"
            ) from err
        except HCAPIError as err:
            raise IntegrationError(
                "An error occurred when trying to fetch the check information"
            ) from err

    @property
    def api_key(self) -> str:
        """API key used by the client."""  # noqa: D401
        return self._api_key


def get_healthchecksio_coordinator_by_api_key(
    hass: HomeAssistant, api_key: str
) -> Optional[HealtchecksioCoordinator]:
    """Return an HealthchecksioClient instance if the API key is managed by an existing client."""
    coordinators: list[HealtchecksioCoordinator] = hass.data[DOMAIN][KEY_COORDINATORS]

    for coordinator in coordinators:
        if coordinator.api_key == api_key:
            return coordinator
    return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up healthchecksio from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(KEY_COORDINATORS, [])
    hass.data[DOMAIN].setdefault(KEY_COORDINATOR_CONFIG_LOCK, Lock())

    api_key = entry.data[CONF_API_KEY]

    coordinator_config_lock: Lock = hass.data[DOMAIN][KEY_COORDINATOR_CONFIG_LOCK]

    async with coordinator_config_lock:
        # Create a new client if no client with this API key exists.
        if (
            coordinator := get_healthchecksio_coordinator_by_api_key(hass, api_key)
        ) is None:
            coordinator = HealtchecksioCoordinator(hass, api_key=api_key)
            hass.data[DOMAIN][KEY_COORDINATORS] += [coordinator]

        await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Unload a config entry."""
#     if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
#         hass.data[DOMAIN].pop(entry.entry_id)

#     return unload_ok
