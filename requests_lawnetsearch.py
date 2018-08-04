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
        with requests.Session() as s:
            # Attempt to access lawnet with existing cookies
            initiate_auth = s.get('https://login.libproxy.smu.edu.sg/login?auth=shibboleth&url=https://www.lawnet.sg/lawnet/web/lawnet/ip-access')
            if initiate_auth.url == 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search':
                return 'SUCCESS'
            soup = BeautifulSoup(initiate_auth.text, 'lxml')
            try:
                saml_payload = {
                    'SAMLRequest': soup.find('input', {'name': 'SAMLRequest'}).get('value'),
                    'RelayState': soup.find('input', {'name': 'SAMLRequest'}).get('value')
                }
            except Exception:
                # TODO Show a GUI failure
                print('Could not find necessary SAML tokens')
                return 'FAIL'
            # Otherwise access the SMU login page
            auth_response = s.post('https://login.smu.edu.sg/adfs/ls/', data=saml_payload)
            if auth_response.url != 'https://login.smu.edu.sg/adfs/ls/':
                return 'FAIL'

            headers = {
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache',
                'Origin': 'https://login.smu.edu.sg',
                'Upgrade-Insecure-Requests': '1',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Referer': 'https://login.smu.edu.sg/adfs/ls/',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9,zh-SG;q=0.8,zh;q=0.7',
            }
            login_payload = {
                'UserName': f'{self.login_prefix}\\{self.username}',
                'Password': self.password,
                'AuthMethod': 'FormsAuthentication'
            }
            # Login to SMU SSO
            login_response = s.post('https://login.smu.edu.sg/adfs/ls', data=login_payload, headers=headers)
            soup = BeautifulSoup(login_response.text, 'lxml')
            # Obtain SAML Response keys
            try:
                auth_payload = {
                    'SAMLResponse': soup.find('input', {'name': 'SAMLResponse'}).get('value'),
                    'RelayState': soup.find('input', {'name': 'RelayState'}).get('value')
                }
            except Exception:
                return 'FAIL'
            # Send SAML response keys
            auth_response = s.post('https://login.libproxy.smu.edu.sg/Shibboleth.sso/SAML2/POST', data=auth_payload, headers=headers)
            # Check login
            test_response = s.get('https://login.libproxy.smu.edu.sg/login?qurl=https%3a%2f%2fwww.lawnet.sg%2flawnet%2fweb%2flawnet%2fip-access')
            if test_response.url == 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search':
                self.cookies = s.cookies
                return 'SUCCESS'
            else:
                return 'FAIL'

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
            s.cookies = self.cookies
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
                try:
                    return self.save_html2pdf(case_citation, case_response.text)
                except:
                    return self.save_html(case_citation, case_response.text)
