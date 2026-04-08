from django.db import models


class Fornecedor(models.Model):
    nome = models.CharField(max_length=150, unique=True, verbose_name='Nome')
    documento = models.CharField(
        max_length=18, blank=True, verbose_name='CPF / CNPJ'
    )
    contato = models.CharField(max_length=200, blank=True, verbose_name='Contato')
    email = models.EmailField(blank=True, verbose_name='E-mail')
    telefone = models.CharField(max_length=20, blank=True, verbose_name='Telefone')
    tags = models.ManyToManyField(
        'core.TagFornecedor',
        blank=True,
        related_name='fornecedores',
        verbose_name='Tags'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['nome']

    def __str__(self):
        return self.nome