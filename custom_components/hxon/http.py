"""Hxon http apis."""
from __future__ import annotations

import json
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    ADD_TOPIC_URL,
    DEL_TOPIC_URL,
    FETCH_TOPICS_URL,
    EDIT_TOPIC_URL,
    TOPIC_PREFIX,
    VALIDATE_USER_URL
)

_LOGGING = logging.getLogger(__name__)


class HxonHttp:
    """Send http requests to hxon service."""

    def __init__(self, hass: HomeAssistant, username: str, password: str) -> None:
        """Initialize."""
        self._hass = hass
        self._username = username
        self._password = password
        self._token = ""

    async def async_validate_user(self) -> dict[str, str]:
        """Fetch all topics created by us from hxon service."""
        session = async_get_clientsession(self._hass)
        data = {
            "username": self._username,
            "password": self._password,
        }
        headers = {'content-type': 'application/json'}
        async with session.post(
                VALIDATE_USER_URL,
                data=json.dumps(data),headers=headers
        ) as res:
            # _LOGGING.error(res)
            res.raise_for_status()
            res_dict = await res.json(content_type="application/json", encoding="utf-8")
            # _LOGGING.error(res_dict)
            if res_dict["code"] == 200 and res_dict["msg"] == "操作成功":
                self._token = res_dict["token"]
                return True
            else:
                return False

    async def async_fetch_all_topics(self) -> dict[str, str]:
        """Fetch all topics created by us from hxon service."""
        headers = {'content-type': 'application/json',"Authorization": "Bearer "+self._token }
        # _LOGGING.error(headers)
        session = async_get_clientsession(self._hass)
        async with session.get(
                FETCH_TOPICS_URL,
                headers=headers
        ) as res:
            # _LOGGING.error(res)
            res.raise_for_status()
            res_dict = await res.json(content_type="application/json", encoding="utf-8")
            _LOGGING.error("followed info is res_dict of fetch all topic")
            _LOGGING.error(res_dict)
            if res_dict["code"] == 200:
                return {
                    topic["devTopic"]: topic["devName"]
                    for topic in res_dict["data"]
                    if topic["devTopic"].startswith(TOPIC_PREFIX+self._username)
                }
            return {}

    async def async_add_topic(self, topic: str, name: str) -> None:
        """Add a topic to hxon service."""
        if not topic.startswith(TOPIC_PREFIX):
            return
        headers = {'content-type': 'application/json', "Authorization": "Bearer " + self._token}
        data = {
            "devName": name,
            "devTopic": topic,
            "devUser": self._username
        }
        _LOGGING.error(headers)
        session = async_get_clientsession(self._hass)
        async with session.post(
            ADD_TOPIC_URL,
            headers=headers,
            data=json.dumps(data),
        ) as res:
            res.raise_for_status()
            res_dict = await res.json(content_type="application/json", encoding="utf-8")
            _LOGGING.error("followed info is res_dict of async_add_topic")
            _LOGGING.error(res_dict)

    async def async_update_topic(self, topic: str, name: str) -> None:
        """Update a topic in hxon service."""
        if not topic.startswith(TOPIC_PREFIX):
            return
        headers = {'content-type': 'application/json', "Authorization": "Bearer " + self._token}
        data = {
            "devName": name,
            "devTopic": topic,
            "devUser": self._username
        }
        session = async_get_clientsession(self._hass)
        async with session.post(
            EDIT_TOPIC_URL,
            headers=headers,
            data=json.dumps(data)
        ) as res:
            res.raise_for_status()
            res_dict = await res.json(content_type="application/json", encoding="utf-8")
            _LOGGING.error("followed info is res_dict of async_rename_topic")
            _LOGGING.error(res_dict)

    async def async_del_topic(self, topic: str) -> None:
        """Delete a topic from hxon service."""
        if not topic.startswith(TOPIC_PREFIX):
            return
        headers = {'content-type': 'application/json', "Authorization": "Bearer " + self._token}
        session = async_get_clientsession(self._hass)
        async with session.get(
            DEL_TOPIC_URL+"?topic="+topic,
            headers=headers
        ) as res:
            res.raise_for_status()
            res_dict = await res.json(content_type="application/json", encoding="utf-8")
            _LOGGING.error("followed info is res_dict of async_del_topic")
            _LOGGING.error(res_dict)
