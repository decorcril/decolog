from django import forms
from core.models import Fornecedor


class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = ['nome', 'documento', 'contato', 'email', 'telefone', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Acrílicos Brasil Ltda',
            }),
            'documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CPF ou CNPJ (opcional)',
            }),
            'contato': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do contato',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contato@empresa.com',
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(11) 99999-9999',
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_documento(self):
        documento = self.cleaned_data.get('documento', '')
        # Remove formatação
        doc_limpo = ''.join(filter(str.isdigit, documento))

        # Se vazio, permite
        if not doc_limpo:
            return ''

        # Valida tamanho
        if len(doc_limpo) not in (11, 14):
            raise forms.ValidationError(
                'Documento inválido. Informe um CPF (11 dígitos) ou CNPJ (14 dígitos).'
            )

        # Verifica duplicata — compara só os dígitos
        for f in Fornecedor.objects.all():
            if self.instance.pk and f.pk == self.instance.pk:
                continue
            doc_existente = ''.join(filter(str.isdigit, f.documento))
            if doc_existente and doc_existente == doc_limpo:
                raise forms.ValidationError(
                    'Já existe um fornecedor com este documento.'
                )

        return documento