from django import forms
from produtos.models import Produto


class ProdutoForm(forms.ModelForm):

    class Meta:
        model = Produto
        fields = ['codigo', 'nome', 'categoria', 'unidade_medida', 'descricao', 'ativo']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: CHAP-001, INSU-002... (opcional)',
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Chapa Acrílico Cristal 1020x1020mm 3mm',
            }),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Informações adicionais (cor, dimensões, fornecedor preferencial...)',
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }