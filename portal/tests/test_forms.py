from django.test import TestCase
from portal.forms import CPFField
from django.core.exceptions import ValidationError

class TestFormsUnit(TestCase):
    def setUp(self):
        self.field = CPFField()

    def test_cpf_field_valid_1(self):
        try:
            self.field.clean("529.982.247-25")
        except ValidationError:
            self.fail("CPF 529.982.247-25 should be valid")

    def test_cpf_field_valid_2(self):
        try:
            self.field.clean("299.173.491-46")
        except ValidationError:
            self.fail("CPF 299.173.491-46 should be valid")

    def test_cpf_field_invalid_all_same(self):
        with self.assertRaises(ValidationError):
            self.field.clean("111.111.111-11")

    def test_cpf_field_invalid_wrong_digits(self):
        with self.assertRaises(ValidationError):
            self.field.clean("123.456.789-00")

    def test_cpf_field_invalid_length(self):
        with self.assertRaises(ValidationError):
            self.field.clean("123.45")

    def test_cpf_field_invalid_empty(self):
        with self.assertRaises(ValidationError):
            self.field.clean("")
