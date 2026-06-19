from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from produtos.models import Produto


class RegistroMontagem(models.Model):
    pedido = models.ForeignKey(
        'vendas.Pedido', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='registros_montagem',
        verbose_name='Pedido'
    )
    operador  = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Operador'
    )
    observacao = models.TextField(blank=True, verbose_name='Observação')
    criado_em  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Registro de Montagem'
        verbose_name_plural = 'Registros de Montagem'
        ordering            = ['-criado_em']

    def __str__(self):
        if self.pedido:
            return f'Montagem {self.criado_em:%d/%m/%Y} — Pedido {self.pedido.numero}'
        return f'Montagem {self.criado_em:%d/%m/%Y} — {self.operador.get_full_name() or self.operador.username}'


class ItemMontagem(models.Model):
    registro       = models.ForeignKey(
        RegistroMontagem, on_delete=models.CASCADE, related_name='itens'
    )
    produto        = models.ForeignKey(
        Produto, on_delete=models.PROTECT, verbose_name='Produto'
    )
    quantidade     = models.PositiveIntegerField(default=1, verbose_name='Quantidade')

    class Meta:
        verbose_name        = 'Item de Montagem'
        verbose_name_plural = 'Itens de Montagem'

    def __str__(self):
        return f'{self.quantidade}x {self.produto.nome}'
    
@property
def progresso_montagem(self):
    """Retorna lista com progresso de montagem por produto do pedido."""
    from montagem.models import ItemMontagem
    resultado = []
    for item in self.itens.select_related('produto').all():
        montado = ItemMontagem.objects.filter(
            registro__pedido=self,
            produto=item.produto,
        ).aggregate(total=sum('quantidade'))['total'] or Decimal('0')
        resultado.append({
            'nome':     item.produto.nome,
            'montado':  montado,
            'total':    item.quantidade,
            'completo': montado >= item.quantidade,
            'falta':    max(Decimal('0'), Decimal(str(item.quantidade)) - Decimal(str(montado))),
        })
    return resultado

@property
def montagem_completa(self):
    """True se todos os produtos do pedido foram montados."""
    return all(p['completo'] for p in self.progresso_montagem)