from lawnetsearch import LawnetBrowser
from credentials import login, false_login
from sha_helpers import generate_sha_hash_helper, read_sha_from_file_helper
import pytest
from pathlib import Path

BASE_DIR = Path.cwd()
SHA_DIR = Path(BASE_DIR) / 'tests/sha/'
DOWNLOAD_DIR = Path(BASE_DIR) / 'tests/downloads/'


@pytest.fixture(scope='class')
def browser(request):
    browser = LawnetBrowser()
    request.cls.browser = browser
    yield


@pytest.mark.usefixtures('browser')
class TestRequestsBrowser:
    def test_incorrect_login(self):
        self.browser.update_download_info(false_login['username'],
                                          false_login['password'], 'smustu',
                                          [], DOWNLOAD_DIR)
        login_status = self.browser.login_lawnet()
        assert login_status == 'FAIL'

    def test_correct_login(self):
        self.browser.update_download_info(login['username'], login['password'],
                                          'smustu', [], DOWNLOAD_DIR)
        login_status = self.browser.login_lawnet()
        assert login_status == 'SUCCESS'

    @pytest.mark.vcr()
    @pytest.mark.parametrize(
        'test_citation, expected_title',
        [
            ('[2016] 3 SLR 621', 'Living the Link Pte Ltd (in creditors voluntary liquidation) and others v Tan Lay Tin Tina and others - [2016] 3 SLR 621'),
            ('[1980] 1 Ch. 576', 'Stonegate Securities Ltd. V. Gregory [1979 S. No. 053] - [1980] 1 Ch. 576'),
            ('[1980] 1 Ch 576', 'Stonegate Securities Ltd. V. Gregory [1979 S. No. 053] - [1980] 1 Ch. 576'),
            # ('[1989] 3 MLJ 385', 'html', '[1989] 3 MLJ 385.sha'),
            ('[1992] 2 WLR 367', 'In Re Atlantic Computer Systems Plc. - [1992] 2 WLR 367'),
            ('[1951] 1 A.C. 850', 'Bolton and Others Appellants and Stone Respondent. - [1951] 1 A.C. 850')
        ])
    def test_successful_case_download(self, test_citation, expected_title):
        self.browser.download_case(test_citation)
        downloaded_case_name = f'{expected_title}.pdf'
        downloaded_case_path = Path(DOWNLOAD_DIR) / downloaded_case_name
        sha_file_path = Path(SHA_DIR) / f'{test_citation}.sha'
        # assert file downloaded with correct extension
        assert Path(downloaded_case_path).is_file()

        # assert file is correct
        assert generate_sha_hash_helper(
            downloaded_case_path) == read_sha_from_file_helper(sha_file_path)
        Path.unlink(downloaded_case_path)
