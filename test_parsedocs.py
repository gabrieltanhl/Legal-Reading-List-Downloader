import os
import parsedocs

TEST_DIR = './test-cases'
TEST_CASE_PREFIX = 'test-case'
TEST_OUTPUT_PREFIX = 'test-output'
NO_OF_TESTS = 2

def load_expected_citation_list(test_number):
    expected_citation_list = []
    test_output_path = os.path.join(TEST_DIR, '{}-{}'.format(TEST_OUTPUT_PREFIX, test_number))
    with open(test_output_path) as test_output:
        for row in test_output:
            # remove newline char
            row = row[:-1] if row[-1] == '\n' else row
            expected_citation_list.append(row)

    return set(expected_citation_list)


def test_start_extract_correct_number_of_cases():
    for test_number in range(1, NO_OF_TESTS + 1):
        test_case_path = os.path.join(TEST_DIR, '{}-{}.docx'.format(TEST_CASE_PREFIX, test_number))
        citation_list = parsedocs.start_extract(test_case_path)
        expected_citation_list = load_expected_citation_list(test_number)

        num_citation = len(citation_list)
        num_expected_citation = len(expected_citation_list)
        assert num_citation == num_expected_citation, "Expected {} cases, but found {} cases".format(
        num_expected_citation, num_citation)


def test_start_extract_correct_case_citations():
    for test_number in range(1, NO_OF_TESTS + 1):
        test_case_path = os.path.join(TEST_DIR, '{}-{}.docx'.format(TEST_CASE_PREFIX, test_number))
        citation_list = set(parsedocs.start_extract(test_case_path))
        expected_citation_list = load_expected_citation_list(test_number)
        print(expected_citation_list)

        assert citation_list == expected_citation_list
