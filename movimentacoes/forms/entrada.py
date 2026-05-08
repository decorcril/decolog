from django import forms
from produtos.models import Produto
from core.models import Local, Fornecedor


class ProdutoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.descricao:
            return f'{obj.nome} — {obj.descricao}'
        return obj.nome


class EntradaForm(forms.Form):
    produto = ProdutoChoiceField(
        queryset=Produto.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Produto'
    )
    local = forms.ModelChoiceField(
        queryset=Local.objects.filter(ativo=True, tipo='fabrica'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Local'
    )
    quantidade = forms.DecimalField(
        max_digits=12, decimal_places=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0',
            'step': '1',
            'min': '1',
        }),
        label='Quantidade'
    )
    fornecedor = forms.ModelChoiceField(
        queryset=Fornecedor.objects.filter(ativo=True),
        required=False,
        empty_label='— Nenhum —',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Fornecedor'
    )
    nota_fiscal = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: NF-001234',
        }),
        label='Nota Fiscal'
    )
    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observação opcional...',
        }),
        label='Observação'
    )