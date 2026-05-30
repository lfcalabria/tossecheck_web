from django.test import TestCase
from unittest.mock import Mock
import json
from portal.views import normalizar_cpf, safe_json

class TestUtilsUnit(TestCase):
    def test_normalizar_cpf_with_formatting(self):
        self.assertEqual(normalizar_cpf("123.456.789-09"), "12345678909")

    def test_normalizar_cpf_with_formatting_2(self):
        self.assertEqual(normalizar_cpf("111.222.333-44"), "11122233344")

    def test_normalizar_cpf_empty_string(self):
        self.assertEqual(normalizar_cpf(""), "")

    def test_normalizar_cpf_none(self):
        self.assertEqual(normalizar_cpf(None), "")

    def test_normalizar_cpf_non_digits(self):
        self.assertEqual(normalizar_cpf("abc"), "")

    def test_normalizar_cpf_with_whitespace(self):
        self.assertEqual(normalizar_cpf("  123.456.789-09  "), "12345678909")

    def test_safe_json_valid(self):
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}
        self.assertEqual(safe_json(mock_response), {"key": "value"})

    def test_safe_json_valid_list(self):
        mock_response = Mock()
        mock_response.json.return_value = []
        self.assertEqual(safe_json(mock_response), [])

    def test_safe_json_invalid_value_error(self):
        mock_response = Mock()
        mock_response.json.side_effect = ValueError
        self.assertIsNone(safe_json(mock_response))

    def test_safe_json_invalid_json_decode_error(self):
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        self.assertIsNone(safe_json(mock_response))