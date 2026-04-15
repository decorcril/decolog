document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('dashboard-data');
  const labels = JSON.parse(el.dataset.labels);
  const entradas = JSON.parse(el.dataset.entradas);
  const saidas = JSON.parse(el.dataset.saidas);

  const commonOptions = {
    responsive: true,
    plugins: { legend: { position: 'top' } },
    scales: {
      y: { beginAtZero: true, ticks: { stepSize: 1 } }
    }
  };

  // Gráfico de linha
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

  // Gráfico de barras
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
});