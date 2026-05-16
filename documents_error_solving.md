### Errors and Solutions

1. 
**P** After creating venv, activating that, installing the requirements from txt file there in terminal of vs code. For generating the test samples I got:

(.venv) PS C:\Users\nadia\Downloads\Doculen> python -m src.utils.generate_samples
C:\Users\nadia\Downloads\Doculen\.venv\Scripts\python.exe: Error while finding module specification for 'src.utils.generate_samples' (ModuleNotFoundError: No module named 'src')
(.venv) PS C:\Users\nadia\Downloads\Doculen> 


**S** For solution use terminal or Power Shell:

(.venv) PS C:\Users\nadia\Downloads\Doculen> $env:PYTHONPATH="."
(.venv) PS C:\Users\nadia\Downloads\Doculen> python -m src.utils.generate_samples
Generating 5 sample German invoices...
  Generated: rechnung_001.pdf
  Generated: rechnung_002.pdf
  Generated: rechnung_003.pdf
  Generated: rechnung_004.pdf
  Generated: rechnung_005.pdf

Done. 5 files in data/samples/
(.venv) PS C:\Users\nadia\Downloads\Doculen>



And then test it:

(.venv) PS C:\Users\nadia\Downloads\Doculen> pytest tests/ -v                    
============================================================================== test session starts ==============================================================================
platform win32 -- Python 3.10.11, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\nadia\Downloads\Doculen\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\nadia\Downloads\Doculen
plugins: cov-7.1.0
collected 26 items                                                                                                                                                               

tests/test_ingestion.py::TestCleanText::test_removes_ligatures PASSED                                                                                                      [  3%]
tests/test_ingestion.py::TestCleanText::test_collapses_spaces PASSED                                                                                                       [  7%]
tests/test_ingestion.py::TestCleanText::test_collapses_excess_newlines PASSED                                                                                              [ 11%]
tests/test_ingestion.py::TestCleanText::test_empty_string PASSED                                                                                                           [ 15%]
tests/test_ingestion.py::TestCleanText::test_strips_whitespace PASSED                                                                                                      [ 19%]
tests/test_ingestion.py::TestClassifyDocType::test_invoice_keywords PASSED                                                                                                 [ 23%]
tests/test_ingestion.py::TestClassifyDocType::test_contract_keywords PASSED                                                                                                [ 26%]
tests/test_ingestion.py::TestClassifyDocType::test_report_keywords PASSED                                                                                                  [ 30%]
tests/test_ingestion.py::TestClassifyDocType::test_empty_text PASSED                                                                                                       [ 34%]
tests/test_ingestion.py::TestClassifyDocType::test_random_text PASSED                                                                                                      [ 38%]
tests/test_ingestion.py::TestClassifyDocType::test_case_insensitive PASSED                                                                                                 [ 42%]
tests/test_ingestion.py::TestClassifyDocType::test_german_english_mixed PASSED                                                                                             [ 46%]
tests/test_ingestion.py::TestPageResult::test_char_count_set_on_init PASSED                                                                                                [ 50%]
tests/test_ingestion.py::TestPageResult::test_empty_text PASSED                                                                                                            [ 53%]
tests/test_ingestion.py::TestPageResult::test_confidence_none_for_text PASSED                                                                                              [ 57%]
tests/test_ingestion.py::TestIngestionResult::test_full_text_concatenates_pages PASSED                                                                                     [ 61%]
tests/test_ingestion.py::TestIngestionResult::test_page_count PASSED                                                                                                       [ 65%]
tests/test_ingestion.py::TestIngestionResult::test_success_true_when_text_present PASSED                                                                                   [ 69%]
tests/test_ingestion.py::TestIngestionResult::test_success_false_when_empty PASSED                                                                                         [ 73%]
tests/test_ingestion.py::TestIngestionResult::test_avg_ocr_confidence_none_for_text PASSED                                                                                 [ 76%]
tests/test_ingestion.py::TestIngestionResult::test_avg_ocr_confidence_computed PASSED                                                                                      [ 80%]
tests/test_ingestion.py::TestPDFRouterIntegration::test_process_generated_invoice PASSED                                                                                   [ 84%]
tests/test_ingestion.py::TestPDFRouterIntegration::test_invoice_contains_expected_fields PASSED                                                                            [ 88%]
tests/test_ingestion.py::TestPDFRouterIntegration::test_file_not_found_raises PASSED                                                                                       [ 92%]
tests/test_ingestion.py::TestPDFRouterIntegration::test_non_pdf_raises PASSED                                                                                              [ 96%]
tests/test_ingestion.py::TestPDFRouterIntegration::test_result_has_file_path PASSED                                                                                        [100%]

============================================================================== 26 passed in 0.32s ===============================================================================
(.venv) PS C:\Users\nadia\Downloads\Doculen> 

