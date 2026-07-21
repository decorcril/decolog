from django.db import models
from django.contrib.auth.models import User


class Notificacao(models.Model):

    class Tipo(models.TextChoices):
        PAGAMENTO_PENDENTE   = 'pagamento_pendente', 'Pagamento Pendente'
        PEDIDO_ABERTO        = 'pedido_aberto',      'Pedido em Aberto'
        AGUARD_PRODUCAO      = 'aguard_producao',     'Aguardando Corte'
        AGUARD_MONTAGEM      = 'aguard_montagem',     'Aguardando Montagem'
        PEDIDO_CANCELADO     = 'pedido_cancelado',    'Pedido Cancelado'
        COBRANCA_30_DIAS     = 'cobranca_30_dias',    'Cobrança 30 Dias'
        PICKING              = 'picking', 'Em Separação'
        ESTOQUE_DISPONIVEL   = 'estoque_disponivel', 'Estoque Disponível'


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

    @classmethod
    def notificar(cls, pedido, tipo, usuarios):
        """
        Cria uma notificação não lida para cada usuário informado, referente
        a um evento pontual (ex: pedido entrou em montagem). Evita duplicar
        se o usuário já tiver uma notificação não lida do mesmo tipo/pedido.
        """
        existentes = set(
            cls.objects.filter(
                pedido=pedido, tipo=tipo, lida=False,
                destinatario__in=usuarios,
            ).values_list('destinatario_id', flat=True)
        )
        novas = [
            cls(destinatario=user, pedido=pedido, tipo=tipo)
            for user in usuarios
            if user.pk not in existentes
        ]
        if novas:
            cls.objects.bulk_create(novas)

    @classmethod
    def usuarios_por_grupo(cls, *nomes_grupos):
        """Retorna usuários ativos que são staff OU pertencem a algum dos grupos informados."""
        return User.objects.filter(
            models.Q(is_staff=True) | models.Q(groups__name__in=nomes_grupos),
            is_active=True,
        ).distinct()