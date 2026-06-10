from django import forms
from django_countries import countries
from clientes.models import Cliente


def validar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[i]):
            return False
    return True


def validar_cnpj(cnpj):
    cnpj = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for pesos in [pesos1, pesos2]:
        soma = sum(int(cnpj[i]) * pesos[i] for i in range(len(pesos)))
        digito = 0 if soma % 11 < 2 else 11 - soma % 11
        if digito != int(cnpj[len(pesos)]):
            return False
    return True


class ClienteForm(forms.ModelForm):

    class Meta:
        model = Cliente
        fields = [
            'tipo_pessoa', 'nome', 'nome_fantasia', 'documento',
            'inscricao_estadual', 'inscricao_municipal',
            'email', 'telefone', 'whatsapp', 'contato',
            'pais',
            'cep', 'estado', 'logradouro', 'numero',
            'complemento', 'bairro', 'cidade',
            'codigo_postal', 'regiao',
            'is_fornecedor', 'ativo',
        ]
        widgets = {
            'tipo_pessoa': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'documento': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_documento'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control'}),
            'inscricao_municipal': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_telefone'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_whatsapp'}),
            'contato': forms.TextInput(attrs={'class': 'form-control'}),
            'pais': forms.Select(choices=[('', '---------')] + list(countries),attrs={'class': 'form-select', 'id': 'id_pais'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_cep'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control'}),
            'regiao': forms.TextInput(attrs={'class': 'form-control'}),
            'is_fornecedor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_documento(self):
        documento = self.cleaned_data.get('documento', '').strip()
        pais = self.cleaned_data.get('pais', 'BR')
        tipo_pessoa = self.cleaned_data.get('tipo_pessoa', 'PJ')

        # País estrangeiro — só verifica unicidade, sem validar formato
        if str(pais) != 'BR':
            if documento:
                qs = Cliente.objects.filter(documento=documento)
                if self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise forms.ValidationError('Já existe um cliente cadastrado com este documento.')
            return documento

        # Brasil — valida CPF ou CNPJ
        if not documento:
            raise forms.ValidationError('O documento é obrigatório para clientes brasileiros.')

        apenas_digitos = ''.join(filter(str.isdigit, documento))

        if tipo_pessoa == 'PF':
            if not validar_cpf(apenas_digitos):
                raise forms.ValidationError('CPF inválido.')
        else:
            if not validar_cnpj(apenas_digitos):
                raise forms.ValidationError('CNPJ inválido.')

        # Verifica unicidade
        qs = Cliente.objects.filter(documento=documento)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Já existe um cliente cadastrado com este CPF/CNPJ.')

        return documento