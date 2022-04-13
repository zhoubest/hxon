"""Constants for the hxon integration."""

from typing import Final

DOMAIN: Final = "hxon"

# #### Config ####
CONF_UNAME: Final = "uname"
CONF_UPWD: Final = "upwd"
CONF_INCLUDE_ENTITIES: Final = "include_entities"


# #### Server ####
HTTP_HOST: Final = "http://192.168.31.176:8080/"
MQTT_HOST: Final = "121.5.72.219"
MQTT_PORT: Final = 1883
MQTT_KEEPALIVE: Final = 60
TOPIC_PREFIX: Final = "hxon/"
TOPIC_SUFFIX_LIGHT: Final = "0002"
TOPIC_SUFFIX_FAN: Final = "0003"
TOPIC_SUFFIX_SENSOR: Final = "0004"
TOPIC_SUFFIX_CLIMATE: Final = "0005"
TOPIC_SUFFIX_SWITCH: Final = "0006"
TOPIC_SUFFIX_COVER: Final = "0009"
INTERVAL_PING = 30  # send ping msg every 30s
INTERVAL_NO_PING = 100  # reconnect to mqtt server in 100s without ping msg received
MSG_SEPARATOR: Final = "#"
MSG_ON: Final = "on"
MSG_OFF: Final = "off"
MSG_PAUSE: Final = "pause"  # for covers
MSG_SPEED_COUNT: Final = 4  # for fans, 4 speed supported at most



# #### Service Api ####
FETCH_TOPICS_URL: Final = f"{HTTP_HOST}device/self/list"
FETCH_TOPIC_URL: Final = f"{HTTP_HOST}device/self/fetch/topic"
ADD_TOPIC_URL: Final = f"{HTTP_HOST}device/self/add"
EDIT_TOPIC_URL: Final = f"{HTTP_HOST}device/self/edit"
DEL_TOPIC_URL: Final = f"{HTTP_HOST}device/self/delete/topic"
VALIDATE_USER_URL: Final = f"{HTTP_HOST}validate"
