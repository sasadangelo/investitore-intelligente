document.addEventListener('DOMContentLoaded', function () {
  // URL del CSV contenente i dati dei tassi di interesse BCE
  const csvUrl = 'https://example.com/bce_interest_rates.csv';

  fetch(csvUrl)
    .then(response => response.text())
    .then(data => {
      const labels = [];
      const values = [];

      // Elaborazione del CSV
      const rows = data.split('\n');
      rows.forEach(row => {
        const cols = row.split(',');
        labels.push(cols[0]); // Data
        values.push(parseFloat(cols[1])); // Tasso di interesse
      });

      // Creazione del grafico con Chart.js
      const ctx = document.getElementById('interestChart').getContext('2d');
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Tasso di Interesse BCE',
            data: values,
            borderColor: 'rgba(75, 192, 192, 1)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            fill: true
          }]
        },
        options: {
          scales: {
            x: {
              type: 'time',
              time: {
                unit: 'month'
              }
            },
            y: {
              beginAtZero: true
            }
          }
        }
      });
    })
    .catch(error => console.error('Errore nel caricamento del CSV:', error));
});
