from django.db import models


class TagFornecedor(models.Model):
    nome = models.CharField(max_length=50, unique=True, verbose_name='Tag')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tag de Fornecedor'
        verbose_name_plural = 'Tags de Fornecedores'
        ordering = ['nome']

    def __str__(self):
        return self.nome