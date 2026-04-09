from django import forms
from produtos.models import Produto


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            'codigo', 'nome', 'categoria', 'unidade_medida',
            'cor', 'espessura_mm',
            'largura_cm', 'comprimento_cm', 'altura_cm',
            'diametro_cm', 'profundidade_cm', 'curvatura_cm',
            'estoque_minimo', 'descricao', 'ativo'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Cola Instantânea, Chapa Cristal 3mm...',
            }),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'cor': forms.Select(attrs={'class': 'form-select'}),
            'espessura_mm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 3',
                'step': '0.01',
            }),
            'largura_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0,00',
                'step': '0.01',
            }),
            'comprimento_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0,00',
                'step': '0.01',
            }),
            'altura_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0,00',
                'step': '0.01',
            }),
            'diametro_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0,00',
                'step': '0.01',
            }),
            'profundidade_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0,00',
                'step': '0.01',
            }),
            'curvatura_cm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0,00',
                'step': '0.01',
            }),
            'estoque_minimo': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'step': '0.001',
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição opcional...',
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: CHAP-001, INSU-002...',
}),
        }