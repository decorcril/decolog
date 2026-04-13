from django import forms
from produtos.models import Produto
from core.models import Local
from estoque.models import Estoque


class SaidaForm(forms.Form):
    MOTIVO_CHOICES = [
    ('venda', 'Venda'),
    ('perda', 'Perda / Avaria'),
    ('uso_interno', 'Uso Interno'),
    ('troca', 'Troca'),
    ('publicidade', 'Publicidade'),
    ('reposicao', 'Reposição'),
    ('manutencao', 'Manutenção'),
    ('outro', 'Outro'),
]

    produto = forms.ModelChoiceField(
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
        max_digits=12, decimal_places=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0',
            'step': '0.001',
            'min': '0.001',
        }),
        label='Quantidade'
    )
    motivo = forms.ChoiceField(
        choices=MOTIVO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Motivo'
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
        produto = cleaned_data.get('produto')
        local = cleaned_data.get('local')
        quantidade = cleaned_data.get('quantidade')

        if produto and local and quantidade:
            try:
                saldo = Estoque.objects.get(produto=produto, local=local)
                if saldo.quantidade < quantidade:
                    raise forms.ValidationError(
                        f'Saldo insuficiente. Disponível: '
                        f'{saldo.quantidade} {produto.get_unidade_medida_display()}.'
                    )
            except Estoque.DoesNotExist:
                raise forms.ValidationError('Produto sem estoque neste local.')

        return cleaned_data