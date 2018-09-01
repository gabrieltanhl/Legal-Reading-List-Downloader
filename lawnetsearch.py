import re
import os
from bs4 import BeautifulSoup
from xhtml2pdf import pisa
from collections import namedtuple
import requests
import itertools
import string

SearchResult = namedtuple('SearchResult', ['case_url', 'case_name'])

class LawnetBrowser():
    SMU_LAWNET_PROXY_URL = 'https://login.libproxy.smu.edu.sg/login?qurl=https%3a%2f%2fwww.lawnet.sg%2flawnet%2fweb%2flawnet%2fip-access'
    LAWNET_SEARCH_URL = 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search'
    LAWNET_CASE_URL = 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/page-content?p_p_id=legalresearchpagecontent_WAR_lawnet3legalresearchportlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-2&p_p_col_count=1&_legalresearchpagecontent_WAR_lawnet3legalresearchportlet_action=openContentPage&contentDocID='
    SEARCH_FORM_ACTION = 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/result-page?p_p_id=legalresearchresultpage_WAR_lawnet3legalresearchportlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-2&p_p_col_count=1&_legalresearchresultpage_WAR_lawnet3legalresearchportlet_action=basicSeachActionURL&_legalresearchresultpage_WAR_lawnet3legalresearchportlet_searchType=0'
    PDF_REPORTS = [
        'SLR',
        'Ch',
        'AC',
        'A.C.',
        'WLR',
        'SSAR',
        'SSLR',
        'FMSLR'
    ]

    def __init__(self):
        self.cookies = None
        self.download_dir = None

    def update_download_info(
            self,
            username,
            password,
            login_prefix,
            citation_list,
            download_dir=None,
    ):
        self.username = username
        self.password = password
        self.login_prefix = login_prefix
        self.set_download_directory(download_dir)
        self.citation_list = citation_list

    def set_download_directory(self, download_dir):
        if download_dir:
            self.download_dir = download_dir
        else:
            self.download_dir = os.path.join(
                os.path.expanduser('~'), 'CaseFiles')

        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def login_lawnet(self):
        with requests.Session() as s:
            if self.cookies:
                s.cookies = self.cookies
            # Test existing cookies
            initiate_auth = s.get(
                'https://login.libproxy.smu.edu.sg/login?auth=shibboleth&url=https://www.lawnet.sg/lawnet/web/lawnet/ip-access'
            )
            if initiate_auth.url == 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search':
                return 'SUCCESS'
            soup = BeautifulSoup(initiate_auth.text, 'lxml')
            try:
                saml_payload = {
                    'SAMLRequest':
                    soup.find('input', {
                        'name': 'SAMLRequest'
                    }).get('value'),
                    'RelayState':
                    soup.find('input', {
                        'name': 'RelayState'
                    }).get('value')
                }
            except Exception:
                # TODO Show a GUI failure
                print('Could not find necessary SAML tokens')
                return 'FAIL'
            # Otherwise access the SMU login page
            auth_response = s.post(
                'https://login.smu.edu.sg/adfs/ls/', data=saml_payload)
            if auth_response.url != 'https://login.smu.edu.sg/adfs/ls/':
                return 'FAIL'
            login_payload = {
                'UserName': f'{self.login_prefix}\\{self.username}',
                'Password': self.password,
                'AuthMethod': 'FormsAuthentication'
            }
            # Login to SMU SSO
            login_response = s.post(
                'https://login.smu.edu.sg/adfs/ls', data=login_payload)
            soup = BeautifulSoup(login_response.text, 'lxml')
            # Obtain SAML Response keys
            try:
                auth_payload = {
                    'SAMLResponse':
                    soup.find('input', {
                        'name': 'SAMLResponse'
                    }).get('value'),
                    'RelayState':
                    soup.find('input', {
                        'name': 'RelayState'
                    }).get('value')
                }
            except Exception:
                return 'FAIL'
            # Send SAML response keys
            auth_response = s.post(
                'https://login.libproxy.smu.edu.sg/Shibboleth.sso/SAML2/POST',
                data=auth_payload)
            # Check login
            test_response = s.get(
                'https://login.libproxy.smu.edu.sg/login?qurl=https%3a%2f%2fwww.lawnet.sg%2flawnet%2fweb%2flawnet%2fip-access'
            )
            if test_response.url == 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/legal-research/basic-search':
                self.cookies = s.cookies
                return 'SUCCESS'
            else:
                return 'FAIL'

    def download_case(self, case_citation, lock=None):
        print('Downloading case', case_citation)
        categories = ['1', '2', '4', '5', '6', '7', '8', '27']
        case_citation = case_citation.replace('Ch ', 'Ch. ')

        with requests.Session() as s:
            s.cookies = self.cookies
            search_payload = {
                'grouping': '1',
                'category': categories,
                'basicSearchKey': case_citation
            }
            if lock:
                lock.acquire()  # only 1 thread can post the search request
            search_response = s.post(
                self.SEARCH_FORM_ACTION, data=search_payload)
            if lock:
                lock.release()  # lock is released by the thread

            cases_found = self.get_case_list_html(search_response.text)
            # without javascript, there is a function call with a
            # "resource id" captured within the "onclick" action
            # of the link
            search_results = [SearchResult(case['onclick'], (case.text).strip())
                             for case in cases_found]

            if len(search_results) == 0:
                return ('Unable to find ' + case_citation + '.')

            # if neutral citation - test first result for PDF
            if not any(map(lambda abbrev: abbrev in case_citation, self.PDF_REPORTS)):
                # Get link of first case
                case_id = re.search(r"'(.*)'", search_results[0].case_url).group(1)
                case_url = self.LAWNET_CASE_URL + case_id

                case_response = s.get(case_url)
                case_text = case_response.text
                case_soup = BeautifulSoup(case_text, 'lxml')
                # Find citations on the case page
                citations_found = []
                for citation in case_soup.find_all('span', {'class': 'Citation offhyperlink'}):
                    try:
                        citations_found.append(citation.find('a').contents)
                    except Exception:
                        citations_found.append(citation.contents)

                # Flatten the list
                citations_found = list(itertools.chain.from_iterable(citations_found))
                if case_citation in citations_found:
                    slr_citation = citations_found[0]
                    if 'SLR' in slr_citation and slr_citation in self.citation_list:
                        # Do not download if it is a duplicate
                        return (f'Duplicate of {slr_citation}')
                    else:
                        return self.download_pdf_for_case(s, case_text, search_results[0].case_name)
                else:
                    return ('Unable to find ' + case_citation + '.')
            else:
                case_index = self.get_case_index(search_results, case_citation)
                if case_index is None:
                    return ('Unable to find ' + case_citation + '.')

                doc_id = re.search(r"'(.*)'",
                                   search_results[case_index].case_url).group(1)
                doc_id = doc_id.split('.')[0]

                pdf_url = self.generate_pdf_url(case_citation, doc_id)
                pdf_response = s.get(pdf_url)
                return self.save_pdf(pdf_response.content, search_results[case_index].case_name)

    def generate_pdf_url(self, case_citation, doc_id):
        def pad_four_digit(case_citation):
            resource_name = case_citation.split(' ')
            resource_name[-1] = resource_name[-1].zfill(4)
            return resource_name

        pdf_base_url = 'https://www-lawnet-sg.libproxy.smu.edu.sg/lawnet/group/lawnet/page-content?p_p_id=legalresearchpagecontent_WAR_lawnet3legalresearchportlet&p_p_lifecycle=2&p_p_resource_id=viewPDFSourceDocument'
        if 'SLR' in case_citation:
            resource_name = pad_four_digit(case_citation)
            resource_name = ' '.join(resource_name)
        elif 'SSAR' in case_citation:
            if any(map(lambda year: str(year) in case_citation, range(1985, 2011))):
                resource_name = pad_four_digit(case_citation)
                resource_name = ' '.join(['(1985-2010)'] + resource_name[1:])
            else:
                resource_name = pad_four_digit(case_citation)
                resource_name = ' '.join(resource_name)
        elif 'WLR' in case_citation and any(map(lambda year: str(year) in case_citation, range(2008, 2021))):
            resource_name = case_citation.replace(' ', '-').replace('[', '').replace(']', '')
        elif 'AC' in case_citation:
            case_citation = case_citation.replace(' ', '-')
            resource_name = case_citation
        elif 'A.C.' in case_citation:
            case_citation = case_citation.replace('A.C.', 'AC')
            resource_name = case_citation
        elif 'Ch.' in case_citation:
            case_citation = case_citation.replace('Ch.', 'Ch')
            resource_name = case_citation
        else:
            resource_name = case_citation

        pdf_url = f'{pdf_base_url}&pdfFileName={case_citation}.pdf&pdfFileUri={doc_id}/resource/{resource_name}.pdf'
        return pdf_url

    def download_pdf_for_case(self, session, case_page, filename):
        pdf_url = self.get_pdf_link(case_page)

        if pdf_url:
            pdf_file = session.get(pdf_url)
            return self.save_pdf(pdf_file.content, filename)
        else:
            try:
                return self.save_html2pdf(case_page, filename)
            except Exception:
                return self.save_html(case_page, filename)

    def get_pdf_link(self, case_page):
        case_soup = BeautifulSoup(case_page, 'lxml')

        for link in case_soup.find_all('a'):
            if 'PDF' in link.text and link['href'] != '#':
                return link['href']
        return None

    def get_case_list_html(self, results_html):
        search_soup = BeautifulSoup(results_html, 'lxml')
        case_list = search_soup.select('.document-title')

        return case_list

    def get_case_index(self, case_list, citation):
        case_index = None
        for index, case in enumerate(case_list):
            if citation.lower() in case[1].lower():
                case_index = index
                break
        return case_index

    def clean_filename(self, filename):
        valid_chars = f'_-.()[] {string.ascii_letters}{string.digits}'
        clean_name = ''.join([char for char in filename if char in valid_chars])

        return clean_name

    def save_pdf(self, case_data, filename):
        case_path = os.path.join(self.download_dir, self.clean_filename(filename) + '.pdf')
        with open(case_path, 'wb') as case_file:
            case_file.write(case_data)

        return f'PDF downloaded.'

    def save_html(self, case_data, filename):
        case_path = os.path.join(self.download_dir, self.clean_filename(filename) + '.html')
        with open(case_path, 'w', encoding='utf-8') as case_file:
            case_file.write(case_data)

        return (
            f'PDF not available. HTML version downloaded.'
        )

    def save_html2pdf(self, case_data, filename):
        def cleanup_html(source_html):
            divider = "<div class=\"navi-container\"> </div>"
            new_html = source_html.split(divider)[1]
            return new_html

        case_path = os.path.join(self.download_dir, self.clean_filename(filename) + '.pdf')
        resultFile = open(case_path, "w+b")
        new_html = cleanup_html(case_data)
        pisa.CreatePDF(new_html, dest=resultFile)
        resultFile.close()
        return f'PDF downloaded.'
