document.addEventListener('DOMContentLoaded', function () {
  const csvUrl = 'https://raw.githubusercontent.com/sasadangelo/investo/main/tassi-interesse.csv';

  fetch(csvUrl)
    .then(response => response.text())
    .then(data => {
      const labels = [];
      const values = [];

      // Elaborazione del CSV
      const rows = data.trim().split('\n').slice(1); // Ignora l'header
      let previousValue = null;

      rows.forEach(row => {
        const cols = row.split(',');

        // Converte manualmente la data dd/mm/yyyy in yyyy-mm-dd per il parsing corretto in JavaScript
        const dateParts = cols[0].split('/');
        const formattedDate = `${dateParts[2]}-${dateParts[1]}-${dateParts[0]}`;
        const currentValue = parseFloat(cols[2].replace('%', ''));

        // Aggiungi il valore precedente se esiste, per rendere la linea stabile
        if (previousValue !== null) {
          // Duplica il valore precedente per la data corrente
          labels.push(new Date(formattedDate));
          values.push(previousValue);
        }

        // Aggiungi il valore corrente
        labels.push(new Date(formattedDate));
        values.push(currentValue);

        // Imposta il valore precedente come quello corrente per il prossimo ciclo
        previousValue = currentValue;
      });

      // Crea il grafico
      const ctx = document.getElementById('interestChart').getContext('2d');
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels.reverse(),
          datasets: [{
            label: 'Tasso di Interesse BCE',
            data: values.reverse(),
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
              },
              ticks: {
                maxTicksLimit: 10
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
