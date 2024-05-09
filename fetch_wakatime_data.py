import requests
import os

# Usando a chave API do Wakatime armazenada nas secrets do GitHub
API_KEY = os.getenv('WAKATIME_API_KEY')
url = f'https://wakatime.com/api/v1/users/current/stats/last_7_days?api_key={API_KEY}'
response = requests.get(url)
data = response.json()

# Aqui você pode formatar os dados como preferir
stats = f"## Coding Stats\n\n- Coding Time Last 7 Days: {data['data']['human_readable_total']}"

# Escreve os dados formatados no README.md
with open('README.md', 'w') as file:
    file.write(stats)
