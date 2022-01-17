import requests
import io
import ast
from functools import lru_cache
import urllib.request
import urllib.parse
import digitalio
import busio
import board
from adafruit_epd.ssd1680 import Adafruit_SSD1680
from tide_graphics import Tide_Graphics
import datetime
import pytz
import time


@lru_cache
def query_sunrise_sunset_api(lat, lon, date):
    date_formatted = date[:4]+ '-' + date[4:6] + '-' + date[-2:]
    url = 'https://api.sunrise-sunset.org/json'
    params = {
        'lat': lat,
        'lng': lon,
        'date':date_formatted,
        'formatted':'0'
    }
    try:
        response = requests.post(url, params=params)
        print('queried sun api at ' + str(datetime.datetime.now()))
    except requests.exceptions.RequestException as e:
        response = type('obj', (object,), {'ok' : False})()
    

    if response.ok:
        sun_dict = ast.literal_eval(response.content.decode())
        
        sunrise_utc_str = sun_dict['results']['sunrise']
        sunrise_utc = datetime.datetime.strptime(sunrise_utc_str.split('+')[0], '%Y-%m-%dT%H:%M:%S')
        sunrise = sunrise_utc.replace(tzinfo=datetime.timezone.utc).astimezone(pytz.timezone('America/Los_Angeles'))
        sunrise_str = sunrise.strftime('%H:%M:%S')

        sunset_utc_str = sun_dict['results']['sunset']
        sunset_utc = datetime.datetime.strptime(sunset_utc_str.split('+')[0], '%Y-%m-%dT%H:%M:%S')
        sunset = sunset_utc.replace(tzinfo=datetime.timezone.utc).astimezone(pytz.timezone('America/Los_Angeles'))
        sunset_str = sunset.strftime('%H:%M:%S')

    else:
        sunrise_str, sunset_str = None, None

    return sunrise_str, sunset_str

@lru_cache
def query_tide_height_api(date):
    url = 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter'
    params = {
        'begin_date': date,
        'range':'24',
        'station': '9449988',
        'product':'predictions',
        'datum':'STND',
        'units':'english',
        'time_zone':'lst_ldt',
        'application':'peter_weir',
        'format':'csv'
    }

    try:
        response = requests.post(url, params=params)
        print('queried tide api at ' + response.headers['Date'])
    except requests.exceptions.RequestException as e:
        response = type('obj', (object,), {'ok' : False})()

    if response.ok:
        response_list = response.content.decode().split(',')[2:-1]
        tide_height = [float(height_line.split('\n')[0]) for height_line in response_list]
    else:
        tide_height = None
    return tide_height

@lru_cache
def query_tide_time_api(date):
    url = 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter'
    params = {
        'begin_date': date,
        'range':'24',
        'station': '9449988',
        'product':'predictions',
        'datum':'STND',
        'interval':'hilo',
        'units':'english',
        'time_zone':'lst_ldt',
        'application':'peter_weir',
        'format':'json'
    }

    try:
        response = requests.post(url, params=params)
        print('queried tide api at ' + response.headers['Date'])
    except requests.exceptions.RequestException as e:
        response = type('obj', (object,), {'ok' : False})()

    if response.ok:
        hilo_dict = ast.literal_eval(response.content.decode())
    else:
        hilo_dict = None

    return hilo_dict

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D22)
rst = digitalio.DigitalInOut(board.D27)
busy = digitalio.DigitalInOut(board.D17)

up_button = digitalio.DigitalInOut(board.D6)
up_button.switch_to_input()
down_button = digitalio.DigitalInOut(board.D5)
down_button.switch_to_input()

DEBOUNCE_DELAY = 0.3

LAT = '48.5343'
LON = '-123.0171'

# Initialize the Display
display = Adafruit_SSD1680(
    122, 250, spi, cs_pin=ecs, dc_pin=dc, sramcs_pin=None, rst_pin=rst, busy_pin=busy,
)

display.rotation = 1

gfx = Tide_Graphics(display)

start_time = datetime.datetime.now()

current_date = start_time
current_date_str = current_date.strftime('%Y%m%d')

last_update_date_str = False

while True:
    if last_update_date_str != current_date_str:
        all_ok = True
        
        sunrise, sunset = query_sunrise_sunset_api(LAT, LON, current_date_str)
        if sunrise is None:
            all_ok = False
            print('failed to pull sunrise, clearing sunrise/sunset cache')
            query_sunrise_sunset_api.cache_clear() # overkill

        tide_height = query_tide_height_api(current_date_str)
        if tide_height is None:
            all_ok = False
            print('failed to pull tide height, clearing tide height cache')
            query_tide_height_api.cache_clear()

        hilo_dict = query_tide_time_api(current_date_str)
        if hilo_dict is None:
            all_ok = False
            print('failed to pull tide times, clearing tide times cache')
            query_tide_time_api.cache_clear()

        if all_ok:
            gfx.display_tide(sunrise, sunset, tide_height, hilo_dict)
            last_update_date_str = current_date_str
        
    if up_button.value != down_button.value:
        if not up_button.value:
            current_date = current_date + datetime.timedelta(days=1)
            current_date_str = current_date.strftime('%Y%m%d')
            time.sleep(DEBOUNCE_DELAY)
        if not down_button.value:
            current_date = current_date + datetime.timedelta(days=-1)
            current_date_str = current_date.strftime('%Y%m%d')
            time.sleep(DEBOUNCE_DELAY)
