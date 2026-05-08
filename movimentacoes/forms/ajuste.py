from django import forms
from produtos.models import Produto
from core.models import Local
from estoque.models import Estoque


class ProdutoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.descricao:
            return f'{obj.nome} — {obj.descricao}'
        return obj.nome


class AjusteForm(forms.Form):
    produto = ProdutoChoiceField(
        queryset=Produto.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Produto'
    )
    local = forms.ModelChoiceField(
        queryset=Local.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Local'
    )
    quantidade = forms.DecimalField(
        max_digits=12, decimal_places=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0',
            'step': '1',
            'min': '0',
        }),
        label='Nova Quantidade (saldo correto)'
    )
    observacao = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Motivo do ajuste (obrigatório)...',
        }),
        label='Motivo do Ajuste'
    )