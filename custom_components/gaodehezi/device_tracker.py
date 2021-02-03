"""
Support for gaodehezi
# Author:
    dscao
# Created:
    2021/2/3
配置格式：
device_tracker:
  - platform: gaodehezi
    name: 'car'
    url: 'http://ts.amap.com/ws/tservice/location/getLast?in=PpD2n4pPpfbcHXrtqBux455At2APNUADztzqjDRXPO7Q8ht77MIYUQBmcWqzbRpMqSoYr8qH6pk7WjhKtlft%2B70tcoqB1TgWK59r0TUl1UFoVFrSrGNQDprBmVpTc%2BnIACjmbvoqCf52445RJppwPgfXpTfQWjJp8jTxTAHOV%2BRlugYX3oM2UkpJGtJ1Bbize6RIppHwRzm396Pgch92I80whgc0W06M%2FQ0PX5hVr%2FuNe12ZcSTo5XWQaFiRSgLu5MCHHqD0TIKYpCMdazRxrDpokn5FzTN0Pj%2BzN%2BFcmXHyaBKqDVBTYbamUC6wi%2FYXBUYYp561z%2Fheoc4vcF7T6D9xvzoQ4I%2BPB6T%2F0szvdR%2BZXz69pxUZtBxARq%2BN0j5E2rGk2BT2HopTb4W9G9F6EpTfHUW8HFDF&keyt=4&ent=2'
    cookie: 'sessionid=r4n3d6d4zlzm44ykbixpfho5ohvw652w'
"""
import logging
import asyncio
import json
import time, datetime
import requests
import re
from dateutil.relativedelta import relativedelta 
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from bs4 import BeautifulSoup

from datetime import timedelta
from time import strftime
import homeassistant.util.dt as dt_util
from homeassistant.components import zone
from homeassistant.components.device_tracker import PLATFORM_SCHEMA
from homeassistant.components.device_tracker.const import CONF_SCAN_INTERVAL
from homeassistant.components.device_tracker.legacy import DeviceScanner
from homeassistant.const import (
    CONF_NAME,
    ATTR_GPS_ACCURACY,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    STATE_HOME,
    STATE_NOT_HOME,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import slugify
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util import slugify
from homeassistant.util.location import distance


TYPE_GEOFENCE = "Geofence"

__version__ = '0.1.0'
_Log=logging.getLogger(__name__)

COMPONENT_REPO = 'https://github.com/dscao/gaodehezi/'
DEFAULT_SCAN_INTERVAL = timedelta(seconds=300)
ICON = 'mdi:car'

DEFAULT_NAME = 'gaodehezi'
KEY = 'key'
COOKIE = 'cookie'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(KEY): cv.string,
    vol.Required(COOKIE): cv.string,
    vol.Optional(CONF_NAME, default= DEFAULT_NAME): cv.string,
})


API_URL = "http://ts.amap.com/ws/tservice/location/getLast?in="

async def async_setup_scanner(hass, config, async_see, discovery_info=None):
    interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    sensor_name = config.get(CONF_NAME)
    key = config.get(KEY)
    cookie = config.get(COOKIE)
    url = API_URL + key
    """_Log.info("key:" + key + ";cookie:" + cookie )"""
    scanner = GaodeDeviceScanner(hass, async_see, sensor_name, url, cookie)
    await scanner.async_start(hass, interval)
    return True


class GaodeDeviceScanner(DeviceScanner):
    def __init__(self, hass, async_see, sensor_name: str, url: str, cookie: str):
        """Initialize the scanner."""
        self.hass = hass
        self.async_see = async_see
        self._name = sensor_name
        self._url = url
        self._cookie = cookie
        self._state = None
        self.attributes = {}
    
        
    
    async def async_start(self, hass, interval):
        """Perform a first update and start polling at the given interval."""
        await self.async_update_info()
        interval = max(interval, DEFAULT_SCAN_INTERVAL)
        async_track_time_interval(hass, self.async_update_info, interval)             
            
    
    async def async_update_info(self, now=None):
        """Get the gps info."""
        HEADERS = {
            'Cookie': self._cookie,
            }
        try:
            response = requests.get(self._url, headers = HEADERS)
        except ReadTimeout:
            _Log.error("Connection timeout....")
        except ConnectionError:
            _Log.error("Connection Error....")
        except RequestException:
            _Log.error("Unknown Error")
        '''_Log.info( response ) '''
        res = response.content.decode('utf-8')
        _Log.debug("res:" + res)

        ret = json.loads(res, strict=False)        
        
        if ret['result'] == "false":
            _Log.error("抓包信息已过期，请重新抓包....."+ret['message']) 
        elif ret['result']['status'] == "ok":
            _Log.info("请求服务器信息成功.....") 
            kwargs = {
                "dev_id": slugify("gaodehezi_{}".format(self._name)),
                "host_name": self._name,
                "attributes": {
                    "icon": "mdi:car",
                    "server_time": time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(ret['server_time'])),
                    "temperature": ret['result']['temperature'],
                    "humidity": ret['result']['humidity'],
                    "aqi": ret['result']['aqi'],
                    },
                }
            kwargs["gps"] = ret['location']
            result = await self.async_see(**kwargs)
            return result
            
        else:
            _Log.error("send request error....")       
