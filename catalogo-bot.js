document.addEventListener('DOMContentLoaded', function () {
  const emissioniBotCsvUrl = 'https://raw.githubusercontent.com/sasadangelo/investo/main/emissioni-bot.csv';
  //const quotazioniBotCsvUrl = 'https://raw.githubusercontent.com/sasadangelo/investo/main/quotazioni-bot.csv';

  fetch(emissioniBotCsvUrl)
    .then(response => response.text())
    .then(data => {
      const table = document.createElement('table');
      const thead = table.createTHead();
      const tbody = table.createTBody();

      // Creazione dell'intestazione della tabella
      const headerRow = thead.insertRow();
      const headers = ['Nome BOT', 'Data Emissione', 'Prezzo Emissione', 'Scadenza'];
      headers.forEach(headerText => {
        const th = document.createElement('th');
        th.textContent = headerText;
        headerRow.appendChild(th);
      });

      // Elaborazione dei dati CSV
      const rows = data.trim().split('\n').slice(1); // Ignora l'header
      rows.forEach(row => {
        const cols = row.split(',');
        const nomeBotCell = cols[0]; // Nome BOT
        const dataEmissioneCell = cols[1]; // Data Emissione
        const prezzoEmissioneCell = cols[2]; // Prezzo Emissione
        const scadenzaCell = cols[3]; // Scadenza

        // Crea una riga per i dati
        const tr = tbody.insertRow();
        const tdNomeBOT = tr.insertCell();
        tdNomeBOT.textContent = nomeBotCell;
        const tdDataEmissione = tr.insertCell();
        tdDataEmissione.textContent = dataEmissioneCell;
        const tdPrezzoEmissione = tr.insertCell();
        tdPrezzoEmissione.textContent = prezzoEmissioneCell;
        const tdScdenza = tr.insertCell();
        tdScdenza.textContent = scadenzaCell;
      });

      // Aggiungi la tabella al body della pagina
      document.querySelector('main').appendChild(table);
    })
    .catch(error => console.error('Errore nel caricamento del CSV:', error));
});
