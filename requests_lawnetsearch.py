import requests
import virtualbrowser
import re
import os
from bs4 import BeautifulSoup
from lawnetsearch import LawnetBrowser
import threading

LAWNET_CASE_URL = 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/page-content?p_p_id=legalresearchpagecontent_WAR_lawnet3legalresearchportlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-2&p_p_col_count=1&_legalresearchpagecontent_WAR_lawnet3legalresearchportlet_action=openContentPage&contentDocID='


class RequestLawnetBrowser(LawnetBrowser):
    def login_lawnet(self):
        print('Logging into LawNet')
        self.driver = virtualbrowser.chrome()
        download_status = super().login_lawnet()
        login_cookies = self.driver.get_cookies()

        self.driver.quit()
        print('Browser closed')

        self.cookies = self.make_cookies_requests_compatible(login_cookies)
        return download_status

    def make_cookies_requests_compatible(self, login_cookies):
        for cookie in login_cookies:
            if 'expiry' in cookie:
                cookie['expires'] = cookie['expiry']
                del cookie['expiry']
            if 'httpOnly' in cookie:
                cookie['rest'] = {'HttpOnly': cookie['httpOnly']}
                del cookie['httpOnly']

        return login_cookies

    def download_case(self, case_citation, lock=None):
        print('Downloading case', case_citation)
        categories = ['1', '2', '4', '5', '6', '7', '8', '27']

        with requests.Session() as s:
            s.headers.update(self.HEADERS)
            for cookie in self.cookies:
                s.cookies.set(**cookie)
            # access search page
            response = s.get(self.SMU_LAWNET_PROXY_URL)
            soup = BeautifulSoup(response.text, 'lxml')

            try:
                # get the url to POST to
                form_action = soup.find(
                    'form', {
                        'name':
                        r'_searchbasicformportlet_WAR_lawnet3legalresearchportlet_bsfm'
                    }).get('action')
                # get the secret key embedded within the form
                # this must be POSTed together with the search
                secret_value = soup.find(
                    'input', {
                        'name':
                        '_searchbasicformportlet_WAR_lawnet3legalresearchportlet_formDate'
                    }).get('value')
            except Exception as e:
                return ('Unable to find secret value or form action')

            # generate search payload to POST
            # current category and grouping are just extracted
            # from Chrome
            search_payload = {'grouping':
                              '1',
                              'category':
                              categories,
                              '_searchbasicformportlet_WAR_lawnet3legalresearchportlet_formDate':
                              secret_value,
                              'basicSearchKey':
                              case_citation
                              }
            if lock:
                lock.acquire()  # only 1 thread can post the search request at any time
            search_response = s.post(form_action, data=search_payload)
            if lock:
                lock.release()  # lock is released by the thread

            cases_found = self.get_case_list_html(search_response.text)
            # without javascript, there is a function call with a
            # "resource id" captured within the "onclick" action
            # of the link
            # data structure: tuple - (case url, case text)
            cases_onclick = [(case['onclick'], case.get_text())
                             for case in cases_found]

            case_index = self.get_case_index(cases_onclick, case_citation)

            if case_index is None:
                return ('\nUnable to find ' + case_citation + '.')

            doc_id = re.search(r"'(.*)'",
                               cases_onclick[case_index][0]).group(1)
            case_url = LAWNET_CASE_URL + doc_id

            # get the page
            case_response = s.get(case_url)
            case_soup = BeautifulSoup(case_response.text, 'lxml')

            for link in case_soup.find_all('a'):
                if 'PDF' in link.text and link['href'] != '#':
                    pdf_url = link['href']
                    break
                else:
                    pdf_url = False

            if pdf_url:
                pdf_file = s.get(pdf_url)
                return self.save_pdf(case_citation, pdf_file.content)
            else:
                return self.save_html(case_citation, case_response.text)
