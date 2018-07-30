import os
import parsedocs
import pytest

TEST_DIR = 'tests/test-cases'
TEST_CASE_PREFIX = 'test-case'
TEST_OUTPUT_PREFIX = 'test-output'
NO_OF_TESTS = 2


def load_expected_citation_list(expected_output_file):
    expected_citation_list = []
    test_output_path = os.path.join(os.getcwd(), TEST_DIR,
                                    expected_output_file)
    with open(test_output_path) as test_output:
        for row in test_output:
            # remove newline char
            row = row[:-1] if row[-1] == '\n' else row
            expected_citation_list.append(row)

    return set(expected_citation_list)


@pytest.mark.parametrize('test_case, expected_output', [
    ('test-case-1.docx', 'test-output-1'),
    ('test-case-2.docx', 'test-output-2'),
])
def test_start_extract_correct_number_of_cases(test_case, expected_output):
    test_case_path = os.path.join(os.getcwd(), TEST_DIR, test_case)
    citation_list = parsedocs.start_extract(test_case_path)
    expected_citation_list = load_expected_citation_list(expected_output)

    num_citation = len(citation_list)
    num_expected_citation = len(expected_citation_list)
    assert num_citation == num_expected_citation, "Expected {} cases, but found {} cases".format(
        num_expected_citation, num_citation)


@pytest.mark.parametrize('test_case, expected_output', [
    ('test-case-1.docx', 'test-output-1'),
    ('test-case-2.docx', 'test-output-2'),
])
def test_start_extract_correct_case_citations(test_case, expected_output):
    test_case_path = os.path.join(os.getcwd(), TEST_DIR, test_case)
    citation_list = set(parsedocs.start_extract(test_case_path))
    expected_citation_list = load_expected_citation_list(expected_output)

    assert citation_list == expected_citation_list


@pytest.mark.parametrize('test_case, expected_output', [
    ('test-case-1.docx', 'test-output-stared-1'),
    # ('test-case-2.docx', 'test-output-2'),
])
def test_extract_correct_number_stared_cases(test_case, expected_output):
    test_case_path = os.path.join(os.getcwd(), TEST_DIR, test_case)
    citation_list = parsedocs.start_extract(test_case_path, stared=True)
    expected_citation_list = load_expected_citation_list(expected_output)

    num_citation = len(citation_list)
    num_expected_citation = len(expected_citation_list)
    assert num_citation == num_expected_citation, "Expected {} cases, but found {} cases".format(
        num_expected_citation, num_citation)


@pytest.mark.parametrize(
    'test_case, expected_output',
    [
        ('test-case-1.docx', 'test-output-stared-1'),
        # ('test-case-2.docx', 'test-output-stared-2'),
    ])
def test_extract_correct_stared_case_citations(test_case, expected_output):
    test_case_path = os.path.join(os.getcwd(), TEST_DIR, test_case)
    citation_list = set(parsedocs.start_extract(test_case_path, stared=True))
    expected_citation_list = load_expected_citation_list(expected_output)

    assert citation_list == expected_citation_list
