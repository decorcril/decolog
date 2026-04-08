from django import forms
from core.models import Local


class LocalForm(forms.ModelForm):
    class Meta:
        model = Local
        fields = ['nome', 'tipo', 'endereco', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Fábrica Central',
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select',
            }),
            'endereco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Rua das Flores, 123',
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }