"""Support for hxon service."""
from __future__ import annotations

import hashlib
import logging
import threading
from typing import Any

import paho.mqtt.client as mqtt

from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_STATE_CHANGED,
)
from homeassistant.core import CoreState, HomeAssistant

from .const import (
    INTERVAL_NO_PING,
    INTERVAL_PING,
    MQTT_HOST,
    MQTT_KEEPALIVE,
    MQTT_PORT,
    TOPIC_PREFIX,
)
from .helper import generate_msg, generate_msg_list, generate_topic, resolve_msg

_LOGGING = logging.getLogger(__name__)


class HxonMqtt:
    """Set up mqtt connections to Hxon Service, subscribe topcs and publish messages."""

    _topic_to_entity_id: dict[str, str] = {}
    _remove_listener: Any = None
    _entity_ids: list[str]
    _publish_timer: Any = None
    _reconnect_timer: Any = None

    def __init__(self, hass: HomeAssistant, uname: str, pwd: str, entity_ids: list[str]) -> None:
        """Initialize."""
        self._hass = hass
        self._uname = uname
        self._pwd = pwd
        self._entity_ids = entity_ids
        self._topic_ping = TOPIC_PREFIX + uname+"/ping"

        if self._hass.state == CoreState.running:
            self._connect()
        else:
            # for situations when hass restarts
            self._hass.bus.listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._connect)

    def _connect(self, _event=None) -> None:
        # Init MQTT connection
        _LOGGING.error("---Init MQTT connection---")
        _uid = "hxonha"+hashlib.md5(self._uname.encode("utf-8")).hexdigest()
        self._mqttc = mqtt.Client(_uid, mqtt.MQTTv311)
        self._mqttc.username_pw_set(self._uname, password=self._pwd)
        self._mqttc.connect(MQTT_HOST, port=MQTT_PORT,
                            keepalive=MQTT_KEEPALIVE)
        self._mqttc.on_message = self._mqtt_on_message
        self._mqttc.loop_start()
        for entity_id in self._entity_ids:
            _LOGGING.error("this is entity id:" + entity_id)
            state = self._hass.states.get(entity_id)
            if state is None:
                continue
            topic = generate_topic(self._uname, state.domain, entity_id)
            _LOGGING.error(topic)
            self._topic_to_entity_id[topic] = entity_id
            self._mqttc.publish(
                topic,
                generate_msg(state.domain, state.state, state.attributes),
            )
            self._mqttc.subscribe(topic, 1)

        # Listen for state changes
        self._remove_listener = self._hass.bus.listen(
            EVENT_STATE_CHANGED, self._state_listener
        )

        # Listen for heartbeat packages
        self._mqttc.subscribe(self._topic_ping, 1)
        self._reset_reconnect_timer()

        # Send heartbeat packages to check the connection
        self._publish_timer = threading.Timer(INTERVAL_PING, self._ping)
        self._publish_timer.start()

    def _reset_reconnect_timer(self):
        if self._reconnect_timer is not None:
            self._reconnect_timer.cancel()
        self._reconnect_timer = threading.Timer(
            INTERVAL_NO_PING, self._reconnect)
        self._reconnect_timer.start()

    def _ping(self):
        self._mqttc.publish(self._topic_ping, "ping")
        self._publish_timer = threading.Timer(INTERVAL_PING, self._ping)
        self._publish_timer.start()

    def _reconnect(self):
        self.disconnect()
        self._connect()

    def disconnect(self) -> None:
        """Disconnect from Bamfa service."""

        # Remove timers
        if self._publish_timer is not None:
            self._publish_timer.cancel()
        if self._reconnect_timer is not None:
            self._reconnect_timer.cancel()

        # Unlisten for state changes
        if self._remove_listener is not None:
            self._remove_listener()

        # Destroy MQTT connection
        self._mqttc.loop_stop()
        self._mqttc.disconnect()

    def _state_listener(self, event):
        entity_id = event.data.get("new_state").entity_id
        if entity_id not in self._topic_to_entity_id.values():
            return
        topic = (list(self._topic_to_entity_id.keys()))[
            list(self._topic_to_entity_id.values()).index(entity_id)
        ]
        state = self._hass.states.get(entity_id)
        self._mqttc.publish(
            topic,
            generate_msg(state.domain, state.state, state.attributes),
        )
        _LOGGING.error(generate_msg(
            state.domain, state.state, state.attributes))

    def _mqtt_on_message(self, _mqtt_client, _userdata, message) -> None:
        if message.topic == self._topic_ping:
            self._reset_reconnect_timer()
            return
        entity_id = self._topic_to_entity_id[message.topic]
        _LOGGING.error(entity_id)
        state = self._hass.states.get(entity_id)
        if state is None:
            _LOGGING.error("state is None")
            return
        _LOGGING.error(
            entity_id+" this is entity is followed by domain and attribute")
        _LOGGING.error(state.domain)
        _LOGGING.error(state.attributes)
        (msg_list, actions) = resolve_msg(
            state.domain, message.payload.decode(), state.attributes
        )

        # generate msg from entity to compare to received msg
        my_msg_list = generate_msg_list(
            state.domain, state.state, state.attributes)

        _LOGGING.error("followed is my_msg_list")
        _LOGGING.error(my_msg_list)
        _LOGGING.error("followed is msg_list & actions")
        _LOGGING.error(msg_list)
        _LOGGING.error(actions)

        for action in actions:
            start_index = action[0]
            end_index = min(action[1], len(msg_list), len(my_msg_list))
            if msg_list[start_index:end_index] != my_msg_list[start_index:end_index]:
                data = {ATTR_ENTITY_ID: entity_id}
                if action[4] is not None:
                    data.update(action[4])
                self._hass.services.call(
                    domain=action[2], service=action[3], service_data=data
                )
                break  # call only one service on each msg received
