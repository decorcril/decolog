from .pedido import (
    pedido_list,
    pedido_create,
    pedido_detail,
    pedido_edit,
    pedido_status,
    item_add,
    item_remove,
    item_update,
    comprovante_envio_add,
    comprovante_envio_delete,
    comprovante_envio_editar_info,
)

from .pagamento import (
    pagamento_add,
    pagamento_delete,
)
from .autocomplete import (
    autocomplete_cliente,
    autocomplete_produto,
)
from .frete import calcular_frete_view
from .orcamento import (
    orcamento_list,
    orcamento_create,
    orcamento_detail,
    orcamento_aprovar,
    orcamento_rejeitar,
)

from .producao import (
    laser_list,
    laser_confirmar,
    laser_finalizar,
    montagem_list,
    montagem_finalizar,
    laser_atribuir,
)

from .relatorio import relatorio_comissoes, exportar_comissoes_csv
from .logistica import logistica_list, logistica_historico
from .pdf import pedido_pdf
from .expedicao import expedir_pedido
from .etiqueta import etiquetas_pedido
from .unidade import unidade_pedido