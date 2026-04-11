from django import forms
import re


class LoginForm(forms.Form):
    crmv = forms.CharField(
        label="CRMV",
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "autocomplete": "username",
            "placeholder": "Digite seu CRMV",
        }),
    )
    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "current-password",
            "placeholder": "Digite sua senha",
        }),
    )


class CPFField(forms.CharField):
    def clean(self, value):
        value = super().clean(value)
        digits = re.sub(r"\D", "", value or "")

        if len(digits) != 11:
            raise forms.ValidationError("CPF deve conter 11 dígitos.")

        if digits == digits[0] * 11:
            raise forms.ValidationError("CPF inválido.")

        def calc_digit(cpf_digits, factor_start):
            total = 0
            factor = factor_start
            for digit in cpf_digits:
                total += int(digit) * factor
                factor -= 1
            rest = (total * 10) % 11
            return 0 if rest == 10 else rest

        digit1 = calc_digit(digits[:9], 10)
        digit2 = calc_digit(digits[:10], 11)

        if digit1 != int(digits[9]) or digit2 != int(digits[10]):
            raise forms.ValidationError("CPF inválido.")

        return digits


class BuscarResponsavelForm(forms.Form):
    cpf = CPFField(
        label="CPF do responsável",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "000.000.000-00",
            "autocomplete": "off",
            "inputmode": "numeric",
            "maxlength": "14",
            "id": "cpf",
        }),
    )


class CadastroResponsavelForm(forms.Form):
    cpf = forms.CharField(
        label="CPF",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "readonly": "readonly",
        }),
    )
    nome = forms.CharField(
        label="Nome",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    telefone = forms.CharField(
        label="Telefone",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class PetForm(forms.Form):
    nome = forms.CharField(
        label="Nome",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    tipo = forms.ChoiceField(
        label="Tipo",
        choices=(
            ("cachorro", "Cachorro"),
            ("gato", "Gato"),
        ),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    sexo = forms.ChoiceField(
        label="Sexo",
        choices=(
            ("macho", "Macho"),
            ("femea", "Fêmea"),
        ),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    raca = forms.CharField(
        label="Raça",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    peso = forms.DecimalField(
        label="Peso",
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "step": "0.01",
            "min": "0",
        }),
    )
    altura = forms.DecimalField(
        label="Altura",
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "step": "0.01",
            "min": "0",
        }),
    )
    idade = forms.IntegerField(
        label="Idade",
        min_value=0,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "min": "0",
        }),
    )