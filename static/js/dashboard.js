document.addEventListener('DOMContentLoaded', () => {

  // ══════════════════════════════════════════════════
  // LEITURA DOS DADOS DO DJANGO
  // Os dados são passados via atributos data-* no elemento
  // <script id="dashboard-data"> no template dashboard.html
  // Para adicionar novos dados:
  //   1. Passe o dado no return render() da view
  //   2. Adicione data-nome='{{ variavel|safe }}' no template
  //   3. Leia aqui com JSON.parse(el.dataset.nome)
  // ══════════════════════════════════════════════════
  const el = document.getElementById('dashboard-data');

  const labels = JSON.parse(el.dataset.labels);                             // Datas do período
  const entradas = JSON.parse(el.dataset.entradas);                         // Qtd entradas por dia
  const saidas = JSON.parse(el.dataset.saidas);                             // Qtd saídas por dia
  const transferenciasCount = JSON.parse(el.dataset.transferenciasCount);   // Qtd transferências por dia
  const transferenciasVolume = JSON.parse(el.dataset.transferenciasVolume); // Volume transferido por dia
  const transferenciasporLocal = JSON.parse(el.dataset.transferenciasPorLocal); // Transferências por local
  const isGerente = el.dataset.isGerente === 'true';                        // Se usuário é Gerente/Admin


  // ══════════════════════════════════════════════════
  // OPÇÕES PADRÃO DOS GRÁFICOS
  // Reutilizadas nos gráficos simples
  // Para gráficos com dois eixos Y, crie options específicas
  // ══════════════════════════════════════════════════
  const commonOptions = {
    responsive: true,
    plugins: { legend: { position: 'top' } },
    scales: {
      y: { beginAtZero: true, ticks: { stepSize: 1 } }
    }
  };


  // ══════════════════════════════════════════════════
  // GRÁFICO 1 — LINHA: Evolução de entradas e saídas
  // Mostra a tendência ao longo do período selecionado
  // Para adicionar nova série: copie um objeto do array datasets
  // ══════════════════════════════════════════════════
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


  // ══════════════════════════════════════════════════
  // GRÁFICO 2 — BARRAS: Comparativo de entradas e saídas
  // Facilita comparar volumes em cada dia
  // ══════════════════════════════════════════════════
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


  // ══════════════════════════════════════════════════
  // GRÁFICOS EXCLUSIVOS PARA GERENTE / ADMIN
  // Controlado pelo data-is-gerente no template
  // ══════════════════════════════════════════════════
  if (isGerente) {

    // ── GRÁFICO 3 — BARRAS: Transferências (quantidade e volume) ──
    // Dois eixos Y: esquerdo para quantidade, direito para volume
    if (document.getElementById('graficoTransferencias')) {
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
              yAxisID: 'y',      // Eixo esquerdo
            },
            {
              label: 'Volume Transferido',
              data: transferenciasVolume,
              backgroundColor: 'rgba(108,117,125,0.4)',
              borderRadius: 6,
              yAxisID: 'y1',     // Eixo direito
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
              grid: { drawOnChartArea: false }, // Não sobrepõe a grade do eixo esquerdo
              title: { display: true, text: 'Volume' }
            }
          }
        }
      });
    }

    // ── GRÁFICO 4 — LINHA: Evolução de transferências por local ──
    // Linha sólida = saídas do local | Linha tracejada = entradas no local
    // Cada local recebe uma cor diferente da paleta abaixo
    if (document.getElementById('graficoTransferenciasPorLocal')) {

      // Paleta de cores — adicione mais se tiver muitos locais
      const cores = [
        '#4da3ff', '#20c997', '#dc3545', '#fd7e14',
        '#6f42c1', '#e83e8c', '#ffc107', '#0dcaf0'
      ];

      const datasets = [];
      let i = 0;

      for (const [nome, dados] of Object.entries(transferenciasporLocal)) {
        const cor = cores[i % cores.length];

        // Linha sólida = saídas (o local enviou)
        datasets.push({
          label: `${nome} (saída)`,
          data: dados.saidas,
          borderColor: cor,
          backgroundColor: cor + '20',
          tension: 0.3,
          fill: false,
          borderDash: [],
        });

        // Linha tracejada = entradas (o local recebeu)
        datasets.push({
          label: `${nome} (entrada)`,
          data: dados.entradas,
          borderColor: cor,
          backgroundColor: cor + '10',
          tension: 0.3,
          fill: false,
          borderDash: [5, 5],
        });

        i++;
      }

      new Chart(document.getElementById('graficoTransferenciasPorLocal'), {
        type: 'line',
        data: { labels, datasets },
        options: commonOptions
      });
    }

  } // fim if isGerente

});