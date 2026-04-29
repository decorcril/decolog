document.addEventListener('DOMContentLoaded', () => {

  const el = document.getElementById('dashboard-data');
  if (!el) return;

  const labels          = JSON.parse(el.dataset.labels);
  const entradas        = JSON.parse(el.dataset.entradas);
  const vendas          = JSON.parse(el.dataset.vendas);
  const saidasPorMotivo = JSON.parse(el.dataset.saidasPorMotivo);
  const topProdutos     = JSON.parse(el.dataset.topProdutos);
  const cortesOperador  = JSON.parse(el.dataset.cortesPorOperador);
  const isGerente       = el.dataset.isGerente === 'true';

  if (!isGerente) return;

  const commonOptions = {
    responsive: true,
    plugins: { legend: { position: 'top' } },
    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
  };

  // ── Gráfico 1: Entradas vs Vendas por dia ──
  const ctxEntradasVendas = document.getElementById('graficoEntradasVendas');
  if (ctxEntradasVendas) {
    new Chart(ctxEntradasVendas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Entradas',
            data: entradas,
            borderColor: '#20c997',
            backgroundColor: 'rgba(32,201,151,0.08)',
            tension: 0.3,
            fill: true,
          },
          {
            label: 'Vendas',
            data: vendas,
            borderColor: '#dc3545',
            backgroundColor: 'rgba(220,53,69,0.08)',
            tension: 0.3,
            fill: true,
          }
        ]
      },
      options: commonOptions
    });
  }

  // ── Gráfico 2: Saídas por motivo (rosca) ──
  const ctxMotivos = document.getElementById('graficoMotivos');
  if (ctxMotivos) {
    const coresMotivos = [
      'rgba(220,53,69,0.8)',
      'rgba(32,201,151,0.8)',
      'rgba(77,163,255,0.8)',
      'rgba(253,126,20,0.8)',
      'rgba(111,66,193,0.8)',
      'rgba(232,62,140,0.8)',
      'rgba(255,193,7,0.8)',
      'rgba(13,202,240,0.8)',
    ];
    new Chart(ctxMotivos, {
      type: 'doughnut',
      data: {
        labels: saidasPorMotivo.labels,
        datasets: [{
          data: saidasPorMotivo.data,
          backgroundColor: coresMotivos.slice(0, saidasPorMotivo.labels.length),
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom', labels: { font: { size: 11 } } }
        }
      }
    });
  }

  // ── Gráfico 3: Top 10 produtos mais vendidos (barras horizontais) ──
  const ctxTopProdutos = document.getElementById('graficoTopProdutos');
  if (ctxTopProdutos) {
    new Chart(ctxTopProdutos, {
      type: 'bar',
      data: {
        labels: topProdutos.labels,
        datasets: [{
          label: 'Quantidade Vendida',
          data: topProdutos.data,
          backgroundColor: 'rgba(77,163,255,0.7)',
          borderRadius: 6,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true } }
      }
    });
  }

  // ── Gráfico 4: Cortes por operador (barras) ──
  const ctxCortesOperador = document.getElementById('graficoCortesOperador');
  if (ctxCortesOperador) {
    new Chart(ctxCortesOperador, {
      type: 'bar',
      data: {
        labels: cortesOperador.labels,
        datasets: [{
          label: 'Registros de Corte',
          data: cortesOperador.data,
          backgroundColor: 'rgba(32,201,151,0.7)',
          borderRadius: 6,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
      }
    });
  }

});