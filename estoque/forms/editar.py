from django import forms
from estoque.models import Estoque


class EstoqueMinimoForm(forms.ModelForm):
    estoque_minimo = forms.IntegerField(
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0',
            'min': '0',
        })
    )

    class Meta:
        model = Estoque
        fields = ['estoque_minimo']

    def clean_estoque_minimo(self):
        from decimal import Decimal
        valor = self.cleaned_data.get('estoque_minimo') or 0
        return Decimal(valor)