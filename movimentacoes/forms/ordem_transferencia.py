from django import forms
from core.models import Local
from produtos.models import Produto
from estoque.models import Estoque


class OrdemTransferenciaForm(forms.Form):
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
    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Observação opcional...',
        }),
        label='Observação'
    )

    def clean(self):
        cleaned_data = super().clean()
        origem = cleaned_data.get('local_origem')
        destino = cleaned_data.get('local_destino')
        if origem and destino and origem == destino:
            raise forms.ValidationError('Origem e destino não podem ser iguais.')
        return cleaned_data