"""Config flow for hxon integration."""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import CONF_INCLUDE_ENTITIES, DOMAIN, CONF_UNAME, CONF_UPWD
from .entities_config import ENTITIES_CONFIG, FILTER
from .helper import generate_topic
from .http import HxonHttp

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_UNAME, default=""): str,
        vol.Required(CONF_UPWD, default=""): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for hxon."""
    VERSION = 1

    _user_input: dict[str, Any] = {}
    _http: HxonHttp
    _all_topics: dict[str, str]

    # Hxon Service uses username and password to auth api calls. One shall provide username and password to config this integration.
    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, last_step=False
            )
        # We save the md5 num of each configured username to self.hass.data[DOMAIN].
        # And check if this username has been configured.
        if DOMAIN in self.hass.data:
            name_md5 = hashlib.md5(
                user_input[CONF_UNAME].encode("utf-8")).hexdigest()
            for data in self.hass.data[DOMAIN].values():
                if data["name_md5"] == name_md5:
                    return self.async_show_form(
                        step_id="user",
                        data_schema=STEP_USER_DATA_SCHEMA,
                        errors={"base": "duplicated_username"},
                        last_step=False,
                    )
        self._user_input.update(user_input)
        self._http = HxonHttp(self.hass, self._user_input[CONF_UNAME], self._user_input[CONF_UPWD])
        is_active = await self._http.async_validate_user()
        if not is_active:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors={"base": "invalid_user"},
                last_step=False,
            )
        else:
            return await self.async_step_entities()

    # Hxon Service communicates with devices by mqtt.
    # Each device corresponds to a particular topic whose suffix is a 3-
    # digit number to indicate its type.
    # We guide one to select entities he wants to sync to Hxon Service.
    # Then we make http calls to submit his selection.
    # At this moment, editing selection after configuration is not supported.
    # One may remove this integration and config again to achieve this.
    # When reconfiguring, entities selected last time will be checked by default.
    async def async_step_entities(self, user_input: dict[str, Any] | None = None):
        """Select entities."""
        if user_input is None:
            # fetch topics created by us before.
            self._all_topics = await self._http.async_fetch_all_topics()
            _LOGGER.error("followed is the return of self._http.async_fetch_all_topics")
            _LOGGER.error(self._all_topics)
            # filter entities we support
            entities = sorted(
                filter(
                    lambda item: FILTER not in ENTITIES_CONFIG[item.domain]
                                 or ENTITIES_CONFIG[item.domain][FILTER](item.attributes),
                    self.hass.states.async_all(ENTITIES_CONFIG.keys()),
                ),
                key=lambda item: item.entity_id,
            )

            return self.async_show_form(
                step_id="entities",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_INCLUDE_ENTITIES
                        ): cv.multi_select(
                            {entity.entity_id: entity.name for entity in entities}
                        ),
                    }
                ),
                last_step=True,
            )

        # create topic for heartbeat packages
        TOPIC_PING = "hxon/"+self._user_input[CONF_UNAME]+"/ping"
        if TOPIC_PING not in self._all_topics:
            await self._http.async_add_topic(TOPIC_PING, "ping")
        else:
            # This topic does not matter to entities, remove it for following syncs
            del self._all_topics[TOPIC_PING]

        # start to sync selected entities to Hxon Service
        for entity_id in user_input[CONF_INCLUDE_ENTITIES]:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            topic = generate_topic(
                self._user_input[CONF_UNAME], state.domain, entity_id)
            if topic in self._all_topics:
                # topic has already been configured before, reuse it
                await self._http.async_update_topic(topic, state.name)
                del self._all_topics[topic]
            else:
                # topic not configured before, create it
                await self._http.async_add_topic(topic, state.name)

        # remove the topics we do not need
        for topic in self._all_topics:
            await self._http.async_del_topic(topic)
            del self._all_topics[topic]
        # end to sync

        self._user_input.update(user_input)
        entity_num = len(user_input[CONF_INCLUDE_ENTITIES])
        return self.async_create_entry(
            title=f"Hxon:{self._user_input[CONF_UNAME]} ({entity_num})",
            data=self._user_input,
        )
