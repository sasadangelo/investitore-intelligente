document.addEventListener('DOMContentLoaded', function () {
  const emissioniBotCsvUrl = 'https://raw.githubusercontent.com/sasadangelo/investo/main/emissioni-bot.csv';
  const quotazioniBotCsvUrl = 'https://raw.githubusercontent.com/sasadangelo/investo/main/quotazioni-bot.csv';

  // Funzione per ottenere la data in formato UTC senza ora
  function getDateWithoutTime(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  // Funzione helper per arrotondare e formattare percentuali
  function formatPercent(value) {
    return value.toFixed(2) + '%';
  }

  function isLeapYear(year) {
    return (year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0));
  }

  function normalizeDate(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  function yearfrac(startDate, endDate) {
    const msInDay = 1000 * 60 * 60 * 24;
    const start = normalizeDate(new Date(startDate));
    const end = normalizeDate(new Date(endDate));
    const diffDays = (end - start) / msInDay;

    const yearDays = isLeapYear(start.getFullYear()) ? 366 : 365;

    return diffDays / yearDays;
  }
  fetch(emissioniBotCsvUrl)
    .then(response => response.text())
    .then(data => {
      fetch(quotazioniBotCsvUrl)
        .then(response => response.text())
        .then(quotazioniData => {
          const table = document.createElement('table');
          const thead = table.createTHead();
          const tbody = table.createTBody();

          // Creazione dell'intestazione della tabella
          const headerRow = thead.insertRow();
          const headers = ['Nome BOT', 'ISIN', 'Ultimo Prezzo', 'Data Emissione', 'Prezzo Emissione', 'Scadenza', 'Disaggio Lordo', 'Imposta Disaggio Lordo', 'Rendimento Lordo', 'Rendimento Netto'];
          headers.forEach(headerText => {
            const th = document.createElement('th');
            th.textContent = headerText;
            headerRow.appendChild(th);
          });

          // Elaborazione dei dati CSV
          const emissioniRows = data.trim().split('\n').slice(1); // Ignora l'header
          const quotazioniRows = quotazioniData.trim().split('\n').slice(1); // Ignora l'header

          // Converte le quotazioni in un oggetto per ricerca rapida
          const quotazioni = {};
          quotazioniRows.forEach(row => {
            const cols = row.split(',');
            const nomeBot = cols[0];
            const ultimoPrezzo = cols[2].replace(',', '.'); // Sostituisce la virgola con il punto
            quotazioni[nomeBot] = ultimoPrezzo;
          });

          emissioniRows.forEach(row => {
            const cols = row.split(',');
            const nomeBotCell = cols[0]; // Nome BOT
            const isinBotCell = cols[1]; // ISIN BOT
            const ultimoPrezzoCell = parseFloat(quotazioni[nomeBotCell]);
            const dataEmissioneCell = cols[2]; // Data Emissione
            const prezzoEmissioneCell = parseFloat(cols[3]); // Prezzo Emissione con punto decimale
            const scadenzaCell = cols[4]; // Scadenza

            // Conversione delle date
            const oggi = new Date();
            const dataEmissione = new Date(dataEmissioneCell.split('/').reverse().join('-')); // Formato dd/mm/yyyy → yyyy-mm-dd
            const scadenza = new Date(scadenzaCell.split('/').reverse().join('-'));

            // Rimuoviamo l'ora dalle date per evitare conflitti con il fuso orario
            const scadenzaNoOra = getDateWithoutTime(scadenza);
            const dataEmissioneNoOra = getDateWithoutTime(dataEmissione);
            const oggiNoOra = getDateWithoutTime(oggi);

            // Calcolo del numero di giorni
            const giorniTotali = (scadenzaNoOra - dataEmissioneNoOra) / (1000 * 60 * 60 * 24);
            const giorniResidui = (scadenzaNoOra - oggiNoOra) / (1000 * 60 * 60 * 24);

            // Calcolo del Disaggio Lordo
            let disaggioLordo = 'N/A';
            if (!isNaN(prezzoEmissioneCell) && giorniTotali > 0) {
              disaggioLordo = ((100 - prezzoEmissioneCell) * giorniResidui / giorniTotali).toFixed(6);
            }

            // Calcolo dell'imposta sul  Disaggio Lordo
            let importaDisaggioLordo = 'N/A';
            if (!isNaN(disaggioLordo)) {
              importaDisaggioLordo = (disaggioLordo * 0.125).toFixed(6);
            }

            // Calcola la frazione di anno (assumiamo che yearfrac gestisca bene la normalizzazione)
            const frazioneAnno = yearfrac(oggiNoOra, scadenzaNoOra);

            let rendimentoLordo = 'N/A';
            if (
              !isNaN(ultimoPrezzoCell) && ultimoPrezzoCell > 0 &&
              !isNaN(frazioneAnno) && frazioneAnno > 0
            ) {
              const base = 100 / ultimoPrezzoCell;
              const potenza = 1 / frazioneAnno;
              const rendimento = Math.pow(base, potenza) - 1;
              rendimentoLordo = formatPercent(rendimento * 100);
            }

            let rendimentoNetto = 'N/A';
            const impDisaggioNum = parseFloat(importaDisaggioLordo);
            if (!isNaN(ultimoPrezzoCell) && !isNaN(impDisaggioNum) && frazioneAnno > 0) {
              rendimentoNetto = (Math.pow(100 / (ultimoPrezzoCell + impDisaggioNum), 1 / frazioneAnno) - 1) * 100;
              rendimentoNetto = rendimentoNetto.toFixed(2) + '%';
            }

            // Crea una riga per i dati
            const tr = tbody.insertRow();
            [nomeBotCell, isinBotCell, ultimoPrezzoCell, dataEmissioneCell, prezzoEmissioneCell, scadenzaCell, disaggioLordo, importaDisaggioLordo, rendimentoLordo, rendimentoNetto].forEach(text => {
              const td = tr.insertCell();
              td.textContent = text;
            });
          });

          // Aggiungi la tabella al body della pagina
          document.querySelector('main').appendChild(table);
        })
        .catch(error => console.error('Errore nel caricamento delle quotazioni:', error));
    })
    .catch(error => console.error('Errore nel caricamento delle emissioni:', error));
});
