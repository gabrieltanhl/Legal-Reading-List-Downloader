from lawnetsearch import LawnetBrowser
from credentials import login, false_login
from sha_helpers import generate_sha_hash_helper, read_sha_from_file_helper
import pytest
import os
import threading

BASE_DIR = os.getcwd()
SHA_DIR = os.path.join(BASE_DIR, 'tests/sha/')
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'tests/downloads/')


@pytest.fixture(scope='class')
def browser(request):

    browser = LawnetBrowser()

    request.cls.browser = browser
    yield


@pytest.mark.usefixtures('browser')
class TestRequestsBrowser:
    # @classmethod
    # def setup_class(self):
    #     self.browser = LawnetBrowser(
    #         login['username'], login['password'], DOWNLOAD_DIR)

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
        'test_citation, expected_ext, expected_sha_file',
        [
            ('[2016] 3 SLR 621', 'pdf', '[2016] 3 SLR 621.sha'),
            ('[1980] 1 Ch 576', 'pdf', '[1980] 1 Ch 576.sha'),
            # ('[1989] 3 MLJ 385', 'html', '[1989] 3 MLJ 385.sha'),
            ('[1992] 2 WLR 367', 'pdf', '[1992] 2 WLR 367.sha')
        ])
    def test_case_download(self, test_citation, expected_ext,
                           expected_sha_file):
        search_lock = threading.Lock()
        self.browser.download_case(test_citation, search_lock)
        downloaded_case_name = test_citation + '.' + expected_ext
        downloaded_case_path = os.path.join(DOWNLOAD_DIR, downloaded_case_name)
        sha_file_path = os.path.join(SHA_DIR, expected_sha_file)
        # assert file downloaded with correct extension
        assert (test_citation + '.' + expected_ext) in os.listdir(DOWNLOAD_DIR)

        # assert file is correct
        assert generate_sha_hash_helper(
            downloaded_case_path) == read_sha_from_file_helper(sha_file_path)
        os.remove(downloaded_case_path)
