import parsedocs

def test_start_extract_correct_number_of_cases():
    citation_list = parsedocs.start_extract('./test-cases/test-case-1.docx')
    actual_citation_list = []
    with open('./test-cases/test-output-1') as test_output:
        for row in test_output:
            # exclude newline char
            actual_citation_list.append(row[:-1])
    num_citation_list = len(set(citation_list))
    num_actual_citation_list = len(set(actual_citation_list))

    assert num_citation_list == num_actual_citation_list, f"Expected {num_actual_citation_list} cases, only found {num_citation_list} cases"
