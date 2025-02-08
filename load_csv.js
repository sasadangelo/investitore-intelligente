document.addEventListener('DOMContentLoaded', function () {
  const csvUrl = 'https://raw.githubusercontent.com/sasadangelo/investo/main/tassi-interesse.csv';

  fetch(csvUrl)
    .then(response => response.text())
    .then(data => {
      const table = document.createElement('table');
      const thead = table.createTHead();
      const tbody = table.createTBody();

      // Creazione dell'intestazione della tabella
      const headerRow = thead.insertRow();
      const headers = ['Data', 'Tipo', 'Tasso Interesse'];
      headers.forEach(headerText => {
        const th = document.createElement('th');
        th.textContent = headerText;
        headerRow.appendChild(th);
      });

      // Elaborazione dei dati CSV
      const rows = data.trim().split('\n').slice(1); // Ignora l'header
      rows.forEach(row => {
        const cols = row.split(',');
        const dataCell = cols[0]; // Data
        const tipoCell = cols[1]; // Tipo
        const tassoCell = cols[2]; // Tasso Interesse

        // Crea una riga per i dati
        const tr = tbody.insertRow();
        const tdData = tr.insertCell();
        tdData.textContent = dataCell;
        const tdTipo = tr.insertCell();
        tdTipo.textContent = tipoCell;
        const tdTasso = tr.insertCell();
        tdTasso.textContent = tassoCell;
      });

      // Aggiungi la tabella al body della pagina
      document.querySelector('main').appendChild(table);
    })
    .catch(error => console.error('Errore nel caricamento del CSV:', error));
});
