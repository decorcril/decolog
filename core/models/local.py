from django.db import models


class Local(models.Model):
    TIPO_FABRICA = 'fabrica'
    TIPO_LOJA = 'loja'
    TIPO_CHOICES = [
        (TIPO_FABRICA, 'Fábrica'),
        (TIPO_LOJA, 'Loja'),
    ]

    nome = models.CharField(max_length=100, verbose_name='Nome')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, verbose_name='Tipo')
    endereco = models.CharField(max_length=200, blank=True, verbose_name='Endereço')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Local'
        verbose_name_plural = 'Locais'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_display()})'

    @property
    def is_fabrica(self):
        return self.tipo == self.TIPO_FABRICA

    @property
    def is_loja(self):
        return self.tipo == self.TIPO_LOJA