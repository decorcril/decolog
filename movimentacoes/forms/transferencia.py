from django import forms
from produtos.models import Produto
from core.models import Local
from estoque.models import Estoque


class TransferenciaForm(forms.Form):
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Produto'
    )
    local_origem = forms.ModelChoiceField(
        queryset=Local.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Local de Origem'
    )
    local_destino = forms.ModelChoiceField(
        queryset=Local.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Local de Destino'
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
    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observação opcional...',
        }),
        label='Observação'
    )

    def clean(self):
        cleaned_data = super().clean()
        origem = cleaned_data.get('local_origem')
        destino = cleaned_data.get('local_destino')
        produto = cleaned_data.get('produto')
        quantidade = cleaned_data.get('quantidade')

        if origem and destino and origem == destino:
            raise forms.ValidationError('Origem e destino não podem ser iguais.')

        if destino and produto:
            if destino.is_loja and produto.is_materia_prima:
                raise forms.ValidationError('Loja não pode receber matéria-prima.')

        if produto and origem and quantidade:
            try:
                saldo = Estoque.objects.get(produto=produto, local=origem)
                if saldo.quantidade < quantidade:
                    raise forms.ValidationError(
                        f'Saldo insuficiente. Disponível: '
                        f'{saldo.quantidade} {produto.get_unidade_medida_display()}.'
                    )
            except Estoque.DoesNotExist:
                raise forms.ValidationError('Produto sem estoque neste local.')

        return cleaned_data