from django.db import models
from django.contrib.auth.models import User


class Notificacao(models.Model):

    class Tipo(models.TextChoices):
        PAGAMENTO_PENDENTE = 'pagamento_pendente', 'Pagamento Pendente'
        PEDIDO_ABERTO      = 'pedido_aberto',      'Pedido em Aberto'
        AGUARD_PRODUCAO    = 'aguard_producao',     'Aguardando Corte'
        AGUARD_MONTAGEM    = 'aguard_montagem',     'Aguardando Montagem'

    destinatario = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='notificacoes'
    )
    pedido = models.ForeignKey(
        'vendas.Pedido', on_delete=models.CASCADE,
        related_name='notificacoes'
    )
    tipo      = models.CharField(max_length=30, choices=Tipo.choices)
    lida      = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-criada_em']
        verbose_name        = 'Notificação'
        verbose_name_plural = 'Notificações'

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.pedido.numero} → {self.destinatario.username}'