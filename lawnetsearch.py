import virtualbrowser
import re
import os
from bs4 import BeautifulSoup
import pickle
from xhtml2pdf import pisa


class LawnetBrowser():
    SMU_LAWNET_PROXY_URL = 'https://login.libproxy.smu.edu.sg/login?qurl=https%3a%2f%2fwww.lawnet.sg%2flawnet%2fweb%2flawnet%2fip-access'
    LAWNET_SEARCH_URL = 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search'
    HEADERS = {
        'User-Agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
    }

    def __init__(self, username, password, download_dir=None):
        self.username = username
        self.password = password
        self.driver = None
        self.cookies = None
        self.cookiepath = None
        self.download_dir = None
        self.set_download_directory(download_dir)

    def set_download_directory(self, download_dir):
        if download_dir:
            self.download_dir = download_dir
        else:
            self.download_dir = os.path.join(
                os.path.expanduser('~'), 'CaseFiles')

        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        self.cookiepath = os.path.join(self.download_dir, '.lawnetcookie.pkl')

    def login_lawnet(self):
        self.driver.get(self.SMU_LAWNET_PROXY_URL)

        # if we do not end up at the lawnet searchpage
        if self.driver.current_url != self.LAWNET_SEARCH_URL:
            self.driver.find_element_by_xpath("/html/body/div/h3[3]/a").click()
            username_field = self.driver.find_element_by_id("userNameInput")
            password_field = self.driver.find_element_by_id("passwordInput")
            username_field.send_keys('smustu\\' + self.username)
            password_field.send_keys(self.password)
            self.driver.find_element_by_xpath(
                "//*[@id=\"submitButton\"]").click()

            try:
                login_message = self.driver.find_element_by_id(
                    "errorText").text
                if 'Incorrect user ID or password' in login_message:
                    return 'FAIL'
            except:
                return 'SUCCESS'

    def get_case_list_html(self, results_html):
        search_soup = BeautifulSoup(results_html, 'lxml')
        case_list = search_soup.select('.document-title')

        return case_list

    def get_case_index(self, case_list, citation):
        case_index = None
        for index, case in enumerate(case_list):
            if citation.replace('Ch ', 'Ch. ').lower() in case[1].lower():
                case_index = index
                break

        return case_index

    def save_pdf(self, case_citation, case_data):
        case_path = os.path.join(self.download_dir, case_citation + '.pdf')
        with open(case_path, 'wb') as case_file:
            case_file.write(case_data)

        return f'\nPDF downloaded for {case_citation}.'

    def save_html(self, case_citation, case_data):
        case_path = os.path.join(self.download_dir, case_citation + '.html')
        with open(case_path, 'w', encoding='utf-8') as case_file:
            case_file.write(case_data)

        return (f'\nPDF not available for {case_citation}. HTML version downloaded.')

    def save_html2pdf(self, case_citation, case_data):
        def cleanup_html(source_html):
            divider = "<div class=\"navi-container\"> </div>"
            new_html = source_html.split(divider)[1]
            return new_html

        case_path = os.path.join(self.download_dir, case_citation + '.pdf')
        resultFile = open(case_path, "w+b")
        new_html = cleanup_html(case_data)
        pisa.CreatePDF(new_html, dest=resultFile)
        resultFile.close()
        return f'\nPDF downloaded for {case_citation}.'
