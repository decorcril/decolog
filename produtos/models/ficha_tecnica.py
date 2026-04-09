from django.db import models


class FichaTecnica(models.Model):
    produto = models.OneToOneField(
        'produtos.Produto',
        on_delete=models.CASCADE,
        related_name='ficha_tecnica',
        verbose_name='Produto Final'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    permite_personalizacao = models.BooleanField(
        default=False,
        verbose_name='Permite Personalização',
        help_text='Se ativo, as quantidades podem ser ajustadas por ordem de produção'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ficha Técnica'
        verbose_name_plural = 'Fichas Técnicas'

    def __str__(self):
        return f'Ficha Técnica — {self.produto.nome}'