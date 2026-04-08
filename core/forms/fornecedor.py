from django import forms
from core.models import Fornecedor, TagFornecedor


class TagFornecedorForm(forms.ModelForm):
    class Meta:
        model = TagFornecedor
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Fornecedor de Acrílico',
            }),
        }


class FornecedorForm(forms.ModelForm):
    nova_tag = forms.CharField(
    required=False,
    label='Criar nova tag',
    widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ex: Fornecedor de Cola',
    })
)

    class Meta:
        model = Fornecedor
        fields = ['nome', 'documento', 'contato', 'email', 'telefone', 'tags', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Acrílicos Brasil Ltda',
            }),
            'documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CPF ou CNPJ (opcional)',
            }),
            'contato': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do contato',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contato@empresa.com',
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(11) 99999-9999',
            }),
            'tags': forms.CheckboxSelectMultiple(),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_nome(self):
        nome = self.cleaned_data.get('nome', '').strip()
        qs = Fornecedor.objects.filter(nome__iexact=nome)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Já existe um fornecedor com este nome.')
        return nome

    def clean_documento(self):
        documento = self.cleaned_data.get('documento', '')
        doc_limpo = ''.join(filter(str.isdigit, documento))
        if not doc_limpo:
            return ''
        if len(doc_limpo) not in (11, 14):
            raise forms.ValidationError(
                'Documento inválido. Informe um CPF (11 dígitos) ou CNPJ (14 dígitos).'
            )
        for f in Fornecedor.objects.all():
            if self.instance.pk and f.pk == self.instance.pk:
                continue
            doc_existente = ''.join(filter(str.isdigit, f.documento))
            if doc_existente and doc_existente == doc_limpo:
                raise forms.ValidationError('Já existe um fornecedor com este documento.')
        return documento

    def save(self, commit=True):
        instance = super().save(commit=commit)
        # Cria nova tag se foi digitada
        nova_tag = self.cleaned_data.get('nova_tag', '').strip()
        if nova_tag:
            tag, _ = TagFornecedor.objects.get_or_create(nome__iexact=nova_tag, defaults={'nome': nova_tag})
            instance.tags.add(tag)
        return instance