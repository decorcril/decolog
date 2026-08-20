from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from vendas.models.pedido import Pedido
from django.db.models.signals import post_delete
from django.dispatch import receiver



TWO = Decimal("0.01")


class Pagamento(models.Model):

    class Metodo(models.TextChoices):
        PIX      = "pix",      "PIX"
        DEBITO   = "debit",    "Cartão de Débito"
        CREDITO  = "credit",   "Cartão de Crédito"
        BOLETO   = "boleto",   "Boleto"
        DINHEIRO = "cash",     "Dinheiro"
        TRANSFER = "transfer", "Transferência"

    pedido      = models.ForeignKey(
        Pedido, on_delete=models.CASCADE,
        related_name='pagamentos', verbose_name='Pedido'
    )
    metodo      = models.CharField(
        max_length=20, choices=Metodo.choices,
        verbose_name='Forma de Pagamento'
    )
    valor       = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Valor Pago'
    )
    transacao   = models.CharField(
        max_length=100, blank=True, unique=True, null=True,
        verbose_name='Número de Transação',
        help_text='Código PIX, NSU do cartão, número do boleto etc.'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    pago_em     = models.DateTimeField(auto_now_add=True, verbose_name='Data do Pagamento')
    criado_por  = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Registrado por'
    )

    class Meta:
        verbose_name        = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering            = ['-pago_em']

    def __str__(self):
        return f'{self.get_metodo_display()} — R$ {self.valor} ({self.pedido.numero})'

    def clean(self):
        if self.transacao:
            qs = Pagamento.objects.filter(transacao=self.transacao)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({
                    'transacao': f"O número de transação '{self.transacao}' já foi utilizado em outro pagamento."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.pedido.sync_status()

    def delete(self, *args, **kwargs):
        pedido = self.pedido
        super().delete(*args, **kwargs)
        pedido.sync_status()

class ComprovanteEnvio(models.Model):
    pedido           = models.ForeignKey(
        Pedido, on_delete=models.CASCADE,
        related_name='comprovantes_envio', verbose_name='Pedido'
    )
    arquivo          = models.FileField(upload_to='comprovantes_envio/%Y/%m/', verbose_name='Arquivo')
    nome_original    = models.CharField(max_length=255, blank=True, verbose_name='Nome Original do Arquivo')
    transportadora   = models.CharField(max_length=100, blank=True, verbose_name='Transportadora')
    codigo_rastreio  = models.CharField(max_length=100, blank=True, verbose_name='Código de Rastreio')
    enviado_em       = models.DateTimeField(auto_now_add=True, verbose_name='Anexado em')
    enviado_por      = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Anexado por'
    )

    class Meta:
        verbose_name        = 'Comprovante de Envio/Retirada'
        verbose_name_plural = 'Comprovantes de Envio/Retirada'
        ordering             = ['-enviado_em']

    def __str__(self):
        return f'Comprovante — {self.pedido.numero} ({self.nome_original})'



@receiver(post_delete, sender=ComprovanteEnvio)
def deletar_arquivo_comprovante(sender, instance, **kwargs):
    """Garante que o arquivo no bucket seja removido sempre que o registro for apagado,
    não importa o caminho (view, admin, cascade, shell)."""
    if instance.arquivo:
        instance.arquivo.delete(save=False)