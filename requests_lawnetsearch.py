import requests
import virtualbrowser
import re
import os
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
}

UserName = r'smustu\junxuan.ng.2015'
Password = r'eG3vfHrXnML}oC'
LAWNET_URL = 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/page-content?p_p_id=legalresearchpagecontent_WAR_lawnet3legalresearchportlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-2&p_p_col_count=1&_legalresearchpagecontent_WAR_lawnet3legalresearchportlet_action=openContentPage&contentDocID='


class RequestLawnetBrowser():
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.set_download_directory()
        self.driver = virtualbrowser.chrome()
        self.cookies = None

    def set_download_directory(self):
        self.homedir = os.path.expanduser("~")+'/CaseFiles/'
        if not os.path.exists(self.homedir):
            os.makedirs(self.homedir)
        self.cookiepath = self.homedir + '.lawnetcookie.pkl'

    def login_lawnet(self):
        self.driver.get(
            "https://login.libproxy.smu.edu.sg/login?qurl=https%3a%2f%2fwww.lawnet.sg%2flawnet%2fweb%2flawnet%2fip-access"
        )

        if self.driver.current_url != 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search':
            self.driver.find_element_by_xpath("/html/body/div/h3[3]/a").click()
            username_field = self.driver.find_element_by_id("userNameInput")
            password_field = self.driver.find_element_by_id("passwordInput")
            username_field.send_keys('smustu\\' + self.username)
            password_field.send_keys(self.password)
            self.driver.find_element_by_xpath(
                "//*[@id=\"submitButton\"]").click()
            login_cookies = self.driver.get_cookies()
            self.driver.quit()

            for cookie in login_cookies:
                if 'expiry' in cookie:
                    cookie['expires'] = cookie['expiry']
                    del cookie['expiry']
                if 'httpOnly' in cookie:
                    cookie['rest'] = {'HttpOnly': cookie['httpOnly']}
                    del cookie['httpOnly']

            self.cookies = login_cookies

    def download_case(self, case_citation):
        print('Downloading case', case_citation)
        categories = ['1', '2', '4', '5', '6', '7', '8', '27']
        with requests.Session() as s:
            s.headers.update(HEADERS)
            for cookie in self.cookies:
                s.cookies.set(**cookie)
            # access search page
            response = s.get(
                'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search'
            )
            soup = BeautifulSoup(response.text, 'html.parser')

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
                return ('Unable to find case' + case_citation)

            # generate search payload to POST
            # current category and grouping are just extracted
            # from Chrome
            search_payload = {
                'grouping':
                '1',
                'category':
                categories,
                '_searchbasicformportlet_WAR_lawnet3legalresearchportlet_formDate':
                secret_value,
                'basicSearchKey':
                case_citation
            }

            search_response = s.post(form_action, data=search_payload)

            search_soup = BeautifulSoup(search_response.text, 'lxml')
            cases_found = search_soup.select('.document-title')
            # without javascript, there is a function call with a
            # "resource id" captured within the "onclick" action
            # of the link
            cases_onclick = [(case['onclick'], case.get_text())
                             for case in cases_found]

            case_index = None
            for index, case in enumerate(cases_onclick):
                if case_citation.lower() in case[1].lower():
                    case_index = index
                    break

            if case_index is None:
                return ('\nUnable to find ' + case_citation + '.')

            doc_id = re.search(r"'(.*)'",
                               cases_onclick[case_index][0]).group(1)
            case_url = LAWNET_URL + doc_id

            # get the page
            case_response = s.get(case_url)
            case_soup = BeautifulSoup(case_response.text, 'lxml')
            if 'SLR' in case_citation:
                for link in case_soup.find_all('a'):
                    if 'PDF' in link.text and link['href'] != '#':
                        pdf_url = link['href']

                pdf_file = s.get(pdf_url)
                with open(self.homedir+case_citation+'.pdf', 'wb') as case_file:
                    case_file.write(pdf_file.content)

                return ('\nPDF downloaded for ' + case_citation + '.')
            else:
                with open(self.homedir+case_citation+'.html', 'w') as html_file:
                    html_file.write(case_response.text)
                return ('\nPDF not available for ' + case_citation + '. HTML version downloaded.')

            return search_soup, search_response


def test():
    b = RequestLawnetBrowser(r'smustu\junxuan.ng.2015', r'eG3vfHrXnML}oC')
    b.login_lawnet()
    s = b.download_case('[1994] 1 SLR(R) 513')
    return s
