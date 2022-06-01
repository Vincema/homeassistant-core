"""Config flow for healthchecksio integration."""
from __future__ import annotations

import logging
from typing import Any

from healthchecks_io import (
    AsyncClient,
    Check,
    CheckNotFoundError,
    HCAPIAuthError,
    HCAPIError,
    HCAPIRateLimitError,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.httpx_client import get_async_client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_UNIQUE_ID): cv.string,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input and initiate a client connection.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Strip the user input strings
    data[CONF_API_KEY] = data[CONF_API_KEY].strip()
    data[CONF_UNIQUE_ID] = data[CONF_UNIQUE_ID].strip()

    # Try to get the info of the check using user input credentials
    hcio_aclient: AsyncClient = AsyncClient(
        api_key=data[CONF_API_KEY], client=get_async_client(hass)
    )
    resp: Check = await hcio_aclient.get_check(check_id=data[CONF_UNIQUE_ID])

    # The title is the name of the check
    return {"title": resp.name}


class HealtChecksIoHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for healthchecksio."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except HCAPIAuthError:
                errors["base"] = "invalid_auth"
            except CheckNotFoundError:
                errors["ba"] = "check_not_found"
            except HCAPIRateLimitError:
                errors["base"] = "rate_limit_reached"
            except HCAPIError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_UNIQUE_ID])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
