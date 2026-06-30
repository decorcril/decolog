from .pedido import (
    pedido_list,
    pedido_create,
    pedido_detail,
    pedido_edit,
    pedido_status,
    item_add,
    item_remove,
    item_update,
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
)

from .relatorio import relatorio_comissoes
from .relatorio import relatorio_comissoes, exportar_comissoes_csv
from .producao import laser_list, laser_confirmar, laser_finalizar, laser_atribuir
from .logistica import logistica_list, logistica_historico
from .pdf import pedido_pdf
from .expedicao import expedir_pedido