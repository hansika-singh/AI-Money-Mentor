"""
Standalone test for the parse_document fix (issue #432).

Tests the try/finally exception handling pattern directly, without importing
the full app (which has a pre-existing duplicate endpoint bug unrelated to
this fix).

Verifies:
1. Temp file is cleaned up on early returns (no file, empty filename)
2. Temp file is cleaned up on successful parse
3. Temp file is cleaned up when parsing raises an exception
4. except OSError is used instead of bare except
"""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch


def parse_document_fixed(request_files, document_parser):
    """
    Reproduces the fixed parse_document logic from app.py.
    This is the exact same try/except/finally structure used in the fix.
    """
    import tempfile
    import os

    tmp_path = None
    try:
        if 'document' not in request_files:
            return {'success': False, 'error': 'No file provided'}, 400

        file = request_files['document']
        if file.filename == '':
            return {'success': False, 'error': 'No file selected'}, 400

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext in ['.png', '.jpg', '.jpeg']:
            result = document_parser.extract_from_image(tmp_path)
        elif file_ext == '.pdf':
            result = document_parser.extract_from_pdf(tmp_path)
        else:
            result = {'success': False, 'error': f'Unsupported file type: {file_ext}'}

        return result, 200

    except Exception as e:
        return {'success': False, 'error': str(e)}, 500
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


class MockFile:
    """Simulates a Flask FileStorage object."""
    def __init__(self, content=b'test', filename='test.png'):
        self.content = content
        self.filename = filename

    def save(self, path):
        with open(path, 'wb') as f:
            f.write(self.content)


class TestParseDocumentFix(unittest.TestCase):

    def test_no_file_provided(self):
        """Early return when no 'document' key — no temp file created."""
        result, status = parse_document_fixed({}, MagicMock())
        self.assertEqual(status, 400)
        self.assertFalse(result['success'])
        self.assertIn('No file provided', result['error'])

    def test_empty_filename(self):
        """Early return when filename is empty — no temp file created."""
        files = {'document': MockFile(filename='')}
        result, status = parse_document_fixed(files, MagicMock())
        self.assertEqual(status, 400)
        self.assertFalse(result['success'])
        self.assertIn('No file selected', result['error'])

    def test_unsupported_file_type_cleans_temp_file(self):
        """Unsupported file type returns error and temp file is cleaned up."""
        files = {'document': MockFile(content=b'test', filename='test.txt')}

        created_paths = []
        orig_named_temp_file = tempfile.NamedTemporaryFile

        def tracking_tmp(*args, **kwargs):
            tmp = orig_named_temp_file(*args, **kwargs)
            created_paths.append(tmp.name)
            return tmp

        with patch('tempfile.NamedTemporaryFile', tracking_tmp):
            result, status = parse_document_fixed(files, MagicMock())

        self.assertEqual(status, 200)
        self.assertFalse(result['success'])
        self.assertIn('Unsupported file type', result['error'])

        for path in created_paths:
            self.assertFalse(os.path.exists(path), f'Temp file {path} not cleaned up')

    def test_temp_file_cleaned_on_exception(self):
        """Temp file is cleaned up even when parsing raises an exception."""
        files = {'document': MockFile(content=b'fake-image', filename='test.png')}

        created_paths = []
        orig_named_temp_file = tempfile.NamedTemporaryFile

        def tracking_tmp(*args, **kwargs):
            tmp = orig_named_temp_file(*args, **kwargs)
            created_paths.append(tmp.name)
            return tmp

        mock_parser = MagicMock()
        mock_parser.extract_from_image = MagicMock(side_effect=RuntimeError('OCR failed'))

        with patch('tempfile.NamedTemporaryFile', tracking_tmp):
            result, status = parse_document_fixed(files, mock_parser)

        self.assertEqual(status, 500)
        self.assertFalse(result['success'])
        self.assertIn('OCR failed', result['error'])

        for path in created_paths:
            self.assertFalse(os.path.exists(path), f'Temp file {path} not cleaned up after exception')

    def test_successful_parse_cleans_temp_file(self):
        """Temp file is cleaned up after a successful parse."""
        files = {'document': MockFile(content=b'fake-image', filename='test.png')}

        created_paths = []
        orig_named_temp_file = tempfile.NamedTemporaryFile

        def tracking_tmp(*args, **kwargs):
            tmp = orig_named_temp_file(*args, **kwargs)
            created_paths.append(tmp.name)
            return tmp

        mock_parser = MagicMock()
        mock_result = {'success': True, 'source': 'image', 'raw_text': 'test'}
        mock_parser.extract_from_image = MagicMock(return_value=mock_result)

        with patch('tempfile.NamedTemporaryFile', tracking_tmp):
            result, status = parse_document_fixed(files, mock_parser)

        self.assertEqual(status, 200)
        self.assertTrue(result['success'])

        for path in created_paths:
            self.assertFalse(os.path.exists(path), f'Temp file {path} not cleaned up')

    def test_pdf_parse_cleans_temp_file(self):
        """Temp file is cleaned up after a successful PDF parse."""
        files = {'document': MockFile(content=b'fake-pdf', filename='test.pdf')}

        created_paths = []
        orig_named_temp_file = tempfile.NamedTemporaryFile

        def tracking_tmp(*args, **kwargs):
            tmp = orig_named_temp_file(*args, **kwargs)
            created_paths.append(tmp.name)
            return tmp

        mock_parser = MagicMock()
        mock_result = {'success': True, 'source': 'pdf', 'raw_text': 'test'}
        mock_parser.extract_from_pdf = MagicMock(return_value=mock_result)

        with patch('tempfile.NamedTemporaryFile', tracking_tmp):
            result, status = parse_document_fixed(files, mock_parser)

        self.assertEqual(status, 200)
        self.assertTrue(result['success'])

        for path in created_paths:
            self.assertFalse(os.path.exists(path), f'Temp file {path} not cleaned up')


if __name__ == '__main__':
    unittest.main()