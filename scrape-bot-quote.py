import requests
from bs4 import BeautifulSoup
import csv

# URL della pagina con le quotazioni dei BOT
url = "https://www.teleborsa.it/Quotazioni/BOT"

# Effettua una richiesta GET per ottenere il contenuto della pagina
response = requests.get(url)
response.raise_for_status()  # Verifica che la richiesta sia andata a buon fine

# Analizza il contenuto HTML della pagina
soup = BeautifulSoup(response.text, "html.parser")

# Trova la tabella contenente le quotazioni dei BOT
table = soup.find("table")

# Estrai le righe della tabella
rows = table.find_all("tr")[1:]  # Salta l'intestazione

# Lista per memorizzare i dati estratti
data = []

# Estrai i dati da ogni riga
for row in rows:
    cols = row.find_all("td")
    if len(cols) >= 6:
        titolo = cols[0].get_text(strip=True)
        ora = cols[1].get_text(strip=True)
        ultimo = cols[2].get_text(strip=True)
        var_percent = cols[3].get_text(strip=True)
        apertura = cols[4].get_text(strip=True)
        min_max = cols[5].get_text(strip=True)
        data.append([titolo, ora, ultimo, var_percent, apertura, min_max])

# Scrivi i dati in un file CSV
with open("quotazioni-bot.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Titolo", "Ora", "Ultimo", "Var %", "Apertura", "Min - Max"])
    writer.writerows(data)

print("Dati salvati in 'quotazioni-bot.csv'")
