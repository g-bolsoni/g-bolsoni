import requests
import os
import logging
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_wakatime_stats(api_key):
    url = f'https://wakatime.com/api/v1/users/current/stats/last_7_days?api_key={api_key}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if 'data' in data and 'human_readable_total' in data['data']:
            return data['data']
        else:
            logging.error("Estrutura de dados inesperada recebida da API.")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao acessar a API do Wakatime: {e}")
        return None

def read_current_readme(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        logging.warning(f"{file_path} não encontrado. Criando um novo.")
        return ""

def write_readme(file_path, content):
    with open(file_path, 'w') as file:
        file.write(content)
    logging.info(f"{file_path} atualizado com sucesso.")

def generate_graph(data, output_path):
    dates = [datetime.strptime(day['range']['date'], '%Y-%m-%d') for day in data['daily_average']]
    times = [day['total_seconds'] / 3600 for day in data['daily_average']]  # Converte segundos para horas
    
    plt.figure(figsize=(10, 5))
    plt.bar(dates, times, color='skyblue')
    plt.xlabel('Data')
    plt.ylabel('Horas de Codificação')
    plt.title('Horas de Codificação nos Últimos 7 Dias')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def update_readme(api_key, readme_path, graph_path):
    stats = get_wakatime_stats(api_key)
    if not stats:
        logging.error("Nenhuma estatística foi obtida. Abandonando a atualização do README.")
        return

    human_readable_total = stats['human_readable_total']
    new_stats = f"## Coding Stats\n\n- Coding Time Last 7 Days: {human_readable_total}\n\n![Coding Graph](./{graph_path})\n"
    current_readme = read_current_readme(readme_path)

    if new_stats.strip() != current_readme.strip():
        logging.info("Atualização detectada nos dados. Atualizando README.md.")
        write_readme(readme_path, new_stats)
    else:
        logging.info("Nenhuma mudança detectada nos dados. README.md não foi atualizado.")
    
    generate_graph(stats, graph_path)

if __name__ == "__main__":
    API_KEY = os.getenv('API_KEY')
    if not API_KEY:
        logging.error("A chave de API do Wakatime não foi encontrada nas variáveis de ambiente.")
    else:
        README_PATH = 'README.md'
        GRAPH_PATH = 'coding_graph.png'
        update_readme(API_KEY, README_PATH, GRAPH_PATH)
