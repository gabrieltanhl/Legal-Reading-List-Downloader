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


class lawnetBrowser():
    def __init__(self, username, password, download_dir=None):
        self.username = username
        self.password = password
        self.setDownloadDirectory(download_dir)
        self.browser = virtualbrowser.chrome()

    def setDownloadDirectory(self, download_dir):
        if download_dir:
            self.homedir = download_dir
        else:
            self.homedir = os.path.expanduser("~")+'/CaseFiles/'

        if not os.path.exists(self.homedir):
            os.makedirs(self.homedir)
        self.cookiepath = self.homedir + '.lawnetcookie.pkl'

    def loginLawnet(self):
        driver = self.browser
        driver.get(
            "https://login.libproxy.smu.edu.sg/login?qurl=https%3a%2f%2fwww.lawnet.sg%2flawnet%2fweb%2flawnet%2fip-access")

        if driver.current_url != 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search':
            driver.find_element_by_xpath("/html/body/div/h3[3]/a").click()
            username = driver.find_element_by_id("userNameInput")
            password = driver.find_element_by_id("passwordInput")
            username.send_keys('smustu\\' + self.username)
            password.send_keys(self.password)
            driver.find_element_by_xpath("//*[@id=\"submitButton\"]").click()

    def downloadCase(self, case_citation):
        driver = self.browser
        time.sleep(0.5)
        searchbox = driver.find_element_by_id("basicSearchKey")
        searchbox.send_keys(case_citation)
        searchbox.send_keys(Keys.RETURN)

        # getting html of search results page
        page_source = driver.page_source
        bsObj = BeautifulSoup(page_source, 'lxml')
        case_info = bsObj.select(".document-title")
        case_url = [(i['href'], i.get_text()) for i in case_info]

        # check if the search results contain what we want
        case_titles = [(i[1]).split('-')[-1].strip() for i in case_url]
        # getting html of the specific case
        try:
            driver.get(case_url[case_titles.index(case_citation)][0])
        except:
            # if cannot find, go back to search page and proceed to the next search term
            driver.get(
                'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search')
            return ('\nUnable to find ' + case_citation + '.')

        case_source = driver.page_source
        bsObj = BeautifulSoup(case_source, 'lxml')
        for i in bsObj.find_all('a'):
            if 'PDF' in i.text and i['href'] != '#':
                pdf_url = i['href']

        if 'SLR' in case_citation:
            self.save_cookies()
            pdf_cookies = self.load_cookie_payload()
            pdf_file = requests.get(pdf_url, headers={'cookie': pdf_cookies})
            open(os.path.join(self.homedir, '{}.pdf'.format(case_citation)),
                 'wb').write(pdf_file.content)
            driver.get(
                'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search')
            return ('\nPDF downloaded for ' + case_citation + '.')
        else:
            Html_file = open(self.homedir+str(case_citation)+".html", "w")
            Html_file.write(case_source)
            Html_file.close()
            driver.get(
                'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search')
            return ('\nPDF not available for ' + case_citation + '. Downloaded the HTML version instead.')

    def save_cookies(self):
        try:
            pickle.dump(self.browser.get_cookies(),
                        open(self.cookiepath, "wb"))
        except:
            'save_cookies failed'

    def load_cookie_payload(self):
        saved_cookies = pickle.load(open(self.cookiepath, "rb"))
        cookie_string = ''
        for i in saved_cookies:
            cookie_name = i['name']
            cookie_value = i['value']
            cookie_string += (cookie_name + '='+cookie_value + '; ')
        return cookie_string

    def quit(self):
        self.browser.quit()
        os.remove(self.cookiepath)
