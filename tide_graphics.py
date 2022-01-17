# would be good to make sure high tide times don't overlap (e.g. 2022-07-08)
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from adafruit_epd.epd import Adafruit_EPD

small_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
)
medium_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
large_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24
)

# RGB Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


class Tide_Graphics:
    def __init__(self, display):

        self.small_font = small_font
        self.medium_font = medium_font
        self.large_font = large_font

        self.display = display

        self._sunrise = None
        self._sunset = None
        self._tide_height = None
        self._hilo_dict = None


    def display_tide(self, sunrise, sunset, tide_height, hilo_dict):

        self._sunrise = sunrise
        self._sunset = sunset
        self._tide_height = tide_height
        self._hilo_dict = hilo_dict

        self.update_display()
        

    def update_display(self):
        self.display.fill(Adafruit_EPD.WHITE)
        image = Image.new("RGB", (self.display.width, self.display.height), color=WHITE)
        draw = ImageDraw.Draw(image)

        # Draw the tide line
        xbuf = 10
        ybuf = 30

        preds = np.array(self._tide_height)
        max_pred, min_pred = str(round(max(preds), 1)), str(round(min(preds),1))
        preds = np.concatenate((preds, np.zeros(1), np.zeros(1)))
        ymax = preds.max()
        ymin = preds.min()
        yscale = 60 / (ymax - ymin)

        y = 122 - ybuf - (preds - ymin) * yscale

        x = np.arange(240) + xbuf # api returns tide height every 6 minutes
        x = np.concatenate((x, x[-1:], x[:1]))

        xy = list(zip(x, y))

        #draw.line(xy, fill=0, width=1, joint='curve')
        draw.polygon(xy, fill=BLACK, outline=BLACK)

        # Draw the high and low tide times
        for hilo in self._hilo_dict['predictions']:
            t = hilo['t']
            hilo_time = t.split(' ')[1].lstrip('0')
            if hilo_time[0] == ':':
                hilo_time = '0' + hilo_time
            hilo_x = min(int(hilo_time.split(':')[0])*10, 190)
            hilo_x = max(hilo_x, 50)
            
            v = hilo['v']
            tide_type = hilo['type']
            if tide_type == 'H':
                hilo_y = 0
            else:
                hilo_y = 100

            hilo_text = hilo_time
            draw.text((hilo_x, hilo_y), hilo_text, font=medium_font, fill=BLACK)

        # Draw the displayed date
        month = str(int(t[5:7]))
        day = str(int(t[8:10]))
        draw.text((0, 0), month+'/'+day, font=small_font, fill=BLACK, anchor='lt')

        # Draw highest and lowest tide height labels
        draw.text((0, 32), max_pred, font=small_font, fill=BLACK, anchor='lb')
        draw.text((0, 94), min_pred, font=small_font, fill=BLACK, anchor='lt')

        # Draw sunrise
        sun_r = 5
        hr, mn, sc = self._sunrise.split(':')
        day_fract = (int(hr)*60*60 + int(mn)*60 + int(sc)) / (24*60*60.)
        sunrise_ind = int(round(240 * day_fract))
        sunrise_x = x[sunrise_ind]
        sunrise_y = y[sunrise_ind]
        draw.ellipse((sunrise_x - sun_r, sunrise_y - sun_r, sunrise_x + sun_r, sunrise_y + sun_r), outline=BLACK, width=2)

        # Draw sunset
        hr, mn, sc = self._sunset.split(':')
        day_fract = (int(hr)*60*60 + int(mn)*60 + int(sc)) / (24*60*60.)
        sunset_ind = int(round(240 * day_fract))
        sunset_x = x[sunset_ind]
        sunset_y = y[sunset_ind]
        draw.ellipse((sunset_x - sun_r, sunset_y - sun_r, sunset_x + sun_r, sunset_y + sun_r), outline=BLACK, width=2)
        
        self.display.image(image)
        self.display.display()
