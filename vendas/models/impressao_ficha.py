from django.db import models
from django.contrib.auth.models import User


class ImpressaoFichaEnvio(models.Model):
    """
    Registra cada vez que a Ficha de Envio (PDF) de um pedido é gerada —
    pode acontecer mais de uma vez (reimpressão, reenvio), por isso é
    histórico, não um campo único no Pedido.
    """
    pedido      = models.ForeignKey(
        'vendas.Pedido', on_delete=models.CASCADE,
        related_name='impressoes_ficha', verbose_name='Pedido'
    )
    usuario     = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, verbose_name='Impresso por'
    )
    impresso_em = models.DateTimeField(auto_now_add=True, verbose_name='Impresso em')

    class Meta:
        verbose_name        = 'Impressão de Ficha de Envio'
        verbose_name_plural  = 'Impressões de Ficha de Envio'
        ordering             = ['-impresso_em']

    def __str__(self):
        nome = self.usuario.get_full_name() or self.usuario.username if self.usuario else '—'
        return f'{self.pedido.numero} — {nome} ({self.impresso_em:%d/%m/%Y %H:%M})'