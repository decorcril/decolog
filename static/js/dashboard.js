document.addEventListener('DOMContentLoaded', () => {

  // ── Lê os dados passados pelo Django via data-atributos ──
  // Para adicionar novos dados: adicione data-atributo no template
  // e leia aqui com el.dataset.nomeAtributo
  const el = document.getElementById('dashboard-data');
  const labels = JSON.parse(el.dataset.labels);
  const entradas = JSON.parse(el.dataset.entradas);
  const saidas = JSON.parse(el.dataset.saidas);
  const isGerente = el.dataset.isGerente === 'true';
  const transferenciasCount = JSON.parse(el.dataset.transferenciasCount);
  const transferenciasVolume = JSON.parse(el.dataset.transferenciasVolume);

  // ── Opções comuns dos gráficos ──
  const commonOptions = {
    responsive: true,
    plugins: { legend: { position: 'top' } },
    scales: {
      y: { beginAtZero: true, ticks: { stepSize: 1 } }
    }
  };

  // ── Gráfico de linha: evolução de entradas e saídas ──
  // Para adicionar novas séries: adicione um objeto no array datasets
  new Chart(document.getElementById('graficoLinha'), {
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
          label: 'Saídas',
          data: saidas,
          borderColor: '#dc3545',
          backgroundColor: 'rgba(220,53,69,0.08)',
          tension: 0.3,
          fill: true,
        }
      ]
    },
    options: commonOptions
  });

  // ── Gráfico de barras: comparativo de entradas e saídas ──
  new Chart(document.getElementById('graficoBarras'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Entradas',
          data: entradas,
          backgroundColor: 'rgba(32,201,151,0.7)',
          borderRadius: 6,
        },
        {
          label: 'Saídas',
          data: saidas,
          backgroundColor: 'rgba(220,53,69,0.7)',
          borderRadius: 6,
        }
      ]
    },
    options: commonOptions
  });

  // ── Gráfico de transferências (visível só para Gerente/Admin) ──
  // Controlado pelo data-is-gerente no template
  if (isGerente && document.getElementById('graficoTransferencias')) {
    new Chart(document.getElementById('graficoTransferencias'), {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Nº de Transferências',
            data: transferenciasCount,
            backgroundColor: 'rgba(77,163,255,0.7)',
            borderRadius: 6,
            yAxisID: 'y',
          },
          {
            label: 'Volume Transferido',
            data: transferenciasVolume,
            backgroundColor: 'rgba(108,117,125,0.4)',
            borderRadius: 6,
            yAxisID: 'y1',
          }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'top' } },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { stepSize: 1 },
            title: { display: true, text: 'Transferências' }
          },
          y1: {
            beginAtZero: true,
            position: 'right',
            grid: { drawOnChartArea: false },
            title: { display: true, text: 'Volume' }
          }
        }
      }
    });
  }

});