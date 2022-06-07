"""Config flow for healthchecksio integration."""
from __future__ import annotations

import logging
from typing import Any, cast

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
STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): cv.string,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input and initiate a client connection.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Strip the user input strings
    data[CONF_API_KEY] = data[CONF_API_KEY].strip()
    data[CONF_UNIQUE_ID] = data[CONF_UNIQUE_ID].strip()

    info: dict[str, Any] = {"errors": {}}

    # Try to get the info of the check using user input credentials
    try:
        hcio_aclient: AsyncClient = AsyncClient(
            api_key=data[CONF_API_KEY], client=get_async_client(hass)
        )
        resp: Check = await hcio_aclient.get_check(check_id=data[CONF_UNIQUE_ID])
    except HCAPIAuthError:
        info["errors"]["base"] = "invalid_auth"
    except CheckNotFoundError:
        info["errors"]["base"] = "check_not_found"
    except HCAPIRateLimitError:
        info["errors"]["base"] = "rate_limit_reached"
    except HCAPIError:
        info["errors"]["base"] = "cannot_connect"
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception")
        info["errors"]["base"] = "unknown"
    else:
        # The title is the name of the check
        info["title"] = resp.name

    return info


class HealtChecksIoHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for healthchecksio."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
            )

        info = await validate_input(self.hass, user_input)

        if errors := info["errors"]:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors,
            )

        await self.async_set_unique_id(user_input[CONF_UNIQUE_ID])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=info["title"], description=info["description"], data=user_input
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle configuration by re-auth."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the reauth step."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=STEP_REAUTH_DATA_SCHEMA,
            )

        user_input[CONF_UNIQUE_ID] = self.context["unique_id"]

        info = await validate_input(self.hass, user_input)

        if errors := info["errors"]:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=STEP_REAUTH_DATA_SCHEMA,
                errors=errors,
            )

        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        self.hass.config_entries.async_update_entry(
            cast(config_entries.ConfigEntry, entry), data=user_input
        )
        await self.hass.config_entries.async_reload(self.context["entry_id"])
        return self.async_abort(reason="reauth_successful")
