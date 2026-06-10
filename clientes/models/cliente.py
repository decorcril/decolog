from django.db import models
from django.contrib.auth.models import User
from django_countries.fields import CountryField


class Cliente(models.Model):
    TIPO_PESSOA = [
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
    ]

    ESTADOS = [
        ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'),
        ('BA', 'BA'), ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'),
        ('GO', 'GO'), ('MA', 'MA'), ('MT', 'MT'), ('MS', 'MS'),
        ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'), ('PR', 'PR'),
        ('PE', 'PE'), ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'),
        ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), ('SC', 'SC'),
        ('SP', 'SP'), ('SE', 'SE'), ('TO', 'TO'),
    ]

    # Identificação
    codigo = models.PositiveIntegerField(unique=True, editable=False)
    tipo_pessoa = models.CharField(max_length=2, choices=TIPO_PESSOA, default='PJ')
    nome = models.CharField(max_length=255, verbose_name='Nome / Razão Social')
    nome_fantasia = models.CharField(max_length=255, blank=True, verbose_name='Nome Fantasia')
    documento = models.CharField(max_length=30, blank=True, verbose_name='CPF / CNPJ / Documento')
    inscricao_estadual = models.CharField(max_length=30, blank=True, verbose_name='Inscrição Estadual')
    inscricao_municipal = models.CharField(max_length=30, blank=True, verbose_name='Inscrição Municipal')

    # Contato
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    contato = models.CharField(max_length=255, blank=True, verbose_name='Pessoa de Contato')

    # Endereço
    pais = CountryField(default='BR', verbose_name='País')
    
    # Campos BR
    cep = models.CharField(max_length=10, blank=True, verbose_name='CEP')
    estado = models.CharField(max_length=2, choices=ESTADOS, blank=True, verbose_name='Estado')

    # Campos universais
    logradouro = models.CharField(max_length=255, blank=True, verbose_name='Logradouro / Street')
    numero = models.CharField(max_length=20, blank=True, verbose_name='Número / Number')
    complemento = models.CharField(max_length=255, blank=True, verbose_name='Complemento / Suite')
    bairro = models.CharField(max_length=255, blank=True, verbose_name='Bairro / District')
    cidade = models.CharField(max_length=255, blank=True, verbose_name='Cidade / City')
    codigo_postal = models.CharField(max_length=20, blank=True, verbose_name='Código Postal / ZIP')
    regiao = models.CharField(max_length=100, blank=True, verbose_name='Estado / Province / Region')

    # Flags
    ativo = models.BooleanField(default=True)
    is_fornecedor = models.BooleanField(default=False, verbose_name='É fornecedor?')

    # Auditoria
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='clientes_criados'
    )

    class Meta:
        ordering = ['nome']
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return f'{self.codigo:04d} — {self.nome}'

    def is_brasil(self):
        return str(self.pais) == 'BR'

    def save(self, *args, **kwargs):
        if not self.codigo:
            ultimo = Cliente.objects.order_by('-codigo').first()
            self.codigo = (ultimo.codigo + 1) if ultimo else 1
        super().save(*args, **kwargs)