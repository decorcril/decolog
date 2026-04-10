from django import forms
from decimal import Decimal
from produtos.models import Produto


class ProdutoForm(forms.ModelForm):

    estoque_minimo = forms.IntegerField(
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0',
            'min': '0',
        })
    )

    unidade_medida = forms.ChoiceField(
        required=False,
        choices=[('', '---------')] + Produto.UNIDADE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Produto
        fields = [
            'codigo', 'nome', 'categoria', 'unidade_medida',
            'cor', 'espessura_mm',
            'largura_mm', 'comprimento_mm',
            'largura_cm', 'comprimento_cm', 'altura_cm',
            'diametro_cm', 'profundidade_cm', 'curvatura_cm',
            'estoque_minimo', 'descricao', 'ativo'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: CHAP-001, INSU-002...',
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Cola Instantânea, Chapa Cristal 3mm...',
            }),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'cor': forms.Select(attrs={'class': 'form-select'}),
            'espessura_mm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 3',
                'step': '0.01',
            }),
            'largura_mm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 1030',
                'step': '0.01',
            }),
            'comprimento_mm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 2030',
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
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição opcional...',
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_estoque_minimo(self):
        valor = self.cleaned_data.get('estoque_minimo') or 0
        return Decimal(valor)

    def clean(self):
        cleaned_data = super().clean()
        categoria = cleaned_data.get('categoria')

        if categoria == Produto.CATEGORIA_CHAPA:
            cleaned_data['unidade_medida'] = 'chp'
            if not cleaned_data.get('largura_mm'):
                self.add_error('largura_mm', 'Obrigatório para chapas.')
            if not cleaned_data.get('comprimento_mm'):
                self.add_error('comprimento_mm', 'Obrigatório para chapas.')
            if not cleaned_data.get('espessura_mm'):
                self.add_error('espessura_mm', 'Obrigatório para chapas.')

        if categoria == Produto.CATEGORIA_FINAL:
            if not cleaned_data.get('espessura_mm'):
                self.add_error('espessura_mm', 'Espessura é obrigatória para produtos finais.')

        return cleaned_data