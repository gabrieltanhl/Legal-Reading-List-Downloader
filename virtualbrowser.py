
from selenium import webdriver
import os
import sys

if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

CHROMEPATH = str(application_path)+'/chromedriver'


def chrome():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--screen-size=1920x1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) AppleWebKit/604.5.6 (KHTML, like Gecko) Version/11.0.3 Safari/604.5.6")
    chrome_options.add_argument("--disable-extensions")
    driver = webdriver.Chrome(
        executable_path=CHROMEPATH, chrome_options=chrome_options)

    return driver
