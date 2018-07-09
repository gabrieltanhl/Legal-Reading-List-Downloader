from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select
import time
from bs4 import BeautifulSoup
import virtualbrowser
import requests
import pickle
import os
from lawnetsearch import LawnetBrowser


class ChromeLawnetBrowser(LawnetBrowser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver = virtualbrowser.chrome()

    def download_case(self, case_citation):
        driver = self.driver
        time.sleep(0.5)
        searchbox = driver.find_element_by_id("basicSearchKey")
        searchbox.send_keys(case_citation)
        searchbox.send_keys(Keys.RETURN)

        # getting html of search results page
        case_info = self.get_case_list_html(driver.page_source)

        # data structure: tuple - (case url, case text)
        case_url = [(i['href'], i.get_text()) for i in case_info]

        # check if the search results contain what we want
        # getting html of the specific case
        case_index = self.get_case_index(case_url, case_citation)

        if case_index is not None:
            driver.get(case_url[case_index][0])
        else:
            # if cannot find, go back to search page and proceed to the next search term
            driver.get(
                'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search')
            return ('\nUnable to find ' + case_citation + '.')

        case_source = driver.page_source
        bsObj = BeautifulSoup(case_source, 'lxml')

        # check if the case has a PDF link
        for i in bsObj.find_all('a'):
            if 'PDF' in i.text and i['href'] != '#':
                pdf_url = i['href']
                break
            else:
                pdf_url = False

        # if there is a PDF link, send GET request to download
        if pdf_url is not False:
            self.save_cookies()
            pdf_cookies = self.load_cookie_payload()
            pdf_file = requests.get(pdf_url, headers={'cookie': pdf_cookies})

            driver.get(
                'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search')
            return self.save_pdf(case_citation, pdf_file.content)
        else:  # if not, download the HTML page source
            driver.get(
                'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search')
            return self.save_html(case_citation, case_source)

    def save_cookies(self):
        try:
            pickle.dump(self.driver.get_cookies(),
                        open(self.cookiepath, "wb"))
        except:
            'save_cookies failed'

    def load_cookie_payload(self):
        """
        loads saved cookies so that it can be used to make a GET request to download the case PDF
        """
        saved_cookies = pickle.load(open(self.cookiepath, "rb"))
        cookie_string = ''
        for i in saved_cookies:
            cookie_name = i['name']
            cookie_value = i['value']
            cookie_string += (cookie_name + '='+cookie_value + '; ')
        return cookie_string

    def quit(self):
        self.driver.quit()
        try:
            os.remove(self.cookiepath)
        except:
            print('failed to remove cookies after browser quits')
