#!/usr/bin/env python3
"""
WakaTime README Stats Updater
Atualiza o README.md com estatísticas do WakaTime incluindo:
- Tempo total de coding
- Linguagens mais usadas
- Gráfico de atividade estilo GitHub (baseado em dados acumulados)
"""

import requests
import os
import logging
import re
import json
import base64
from datetime import datetime, timedelta
from pathlib import Path

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes
START_MARKER = "<!-- WAKATIME:START -->"
END_MARKER = "<!-- WAKATIME:END -->"
GRAPH_START = "<!-- WAKATIME_ACTIVITY:START -->"
GRAPH_END = "<!-- WAKATIME_ACTIVITY:END -->"

# Arquivo de histórico
HISTORY_FILE = "wakatime_history.json"

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


class WakaTimeAPI:
    """Cliente para a API do WakaTime"""

    BASE_URL = "https://wakatime.com/api/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Basic {base64.b64encode(api_key.encode()).decode()}"
        }

    def _request(self, endpoint: str, params: dict = None, timeout: int = 30) -> dict:
        """Faz uma requisição à API do WakaTime"""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para {endpoint}: {e}")
            return None

    def get_stats(self, range_type: str = "last_7_days") -> dict:
        """Obtém estatísticas gerais"""
        data = self._request(f"users/current/stats/{range_type}")
        return data.get('data') if data else None

    def get_summaries(self, start: str, end: str) -> list:
        """Obtém resumos diários entre duas datas"""
        data = self._request("users/current/summaries", {
            "start": start,
            "end": end
        }, timeout=60)
        return data.get('data', []) if data else []

    def get_all_time_since_today(self) -> dict:
        """Obtém tempo total de coding desde sempre"""
        data = self._request("users/current/all_time_since_today")
        return data.get('data') if data else None


class HistoryManager:
    """Gerencia o histórico de atividade do WakaTime"""

    def __init__(self, file_path: str = HISTORY_FILE):
        self.file_path = Path(file_path)
        self.data = self._load()

    def _load(self) -> dict:
        """Carrega o histórico do arquivo JSON"""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Histórico carregado: {len(data.get('daily_activity', {}))} dias")
                    return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Erro ao carregar histórico: {e}. Criando novo.")

        return {
            "daily_activity": {},
            "last_updated": None,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }
        }

    def save(self) -> None:
        """Salva o histórico no arquivo JSON"""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        logger.info(f"Histórico salvo: {len(self.data['daily_activity'])} dias")

    def merge_activity(self, new_data: dict) -> int:
        """
        Faz merge dos novos dados com o histórico existente.
        Retorna o número de novos dias adicionados.
        """
        added = 0
        for date, seconds in new_data.items():
            if date not in self.data["daily_activity"]:
                added += 1
            # Sempre atualiza (dados mais recentes podem ser mais precisos)
            self.data["daily_activity"][date] = seconds

        logger.info(f"Merge concluído: {added} novos dias adicionados")
        return added

    def get_activity(self) -> dict:
        """Retorna todos os dados de atividade"""
        return self.data.get("daily_activity", {})

    def get_stats(self) -> dict:
        """Retorna estatísticas do histórico"""
        activity = self.data.get("daily_activity", {})
        if not activity:
            return {"total_days": 0, "total_hours": 0, "first_date": None, "last_date": None}

        dates = sorted(activity.keys())
        total_seconds = sum(activity.values())

        return {
            "total_days": len(activity),
            "total_hours": round(total_seconds / 3600, 1),
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None
        }


def generate_activity_svg(daily_data: dict, weeks: int = 52) -> str:
    """
    Gera um SVG do gráfico de atividade estilo GitHub
    """
    today = datetime.now().date()

    # Configurações do SVG
    cell_size = 10
    cell_spacing = 3
    margin_left = 35
    margin_top = 20

    # Cores (estilo WakaTime/GitHub dark)
    colors = ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353']

    # Calcular data inicial (domingo mais próximo há X semanas)
    days_since_sunday = (today.weekday() + 1) % 7
    start_date = today - timedelta(days=(weeks * 7) + days_since_sunday - 1)

    # Calcular níveis baseado no máximo valor
    values = [v for v in daily_data.values() if v > 0]
    if values:
        # Usar percentil 90 como referência para evitar outliers
        sorted_values = sorted(values)
        p90_idx = int(len(sorted_values) * 0.9)
        max_seconds = sorted_values[p90_idx] if p90_idx < len(sorted_values) else sorted_values[-1]
        max_seconds = max(max_seconds, 3600)  # Mínimo 1 hora para calcular níveis
    else:
        max_seconds = 3600

    def get_level(seconds: int) -> int:
        if seconds == 0:
            return 0
        ratio = seconds / max_seconds
        if ratio < 0.25:
            return 1
        elif ratio < 0.5:
            return 2
        elif ratio < 0.75:
            return 3
        return 4

    # Dimensões
    width = margin_left + (weeks + 1) * (cell_size + cell_spacing) + 30
    height = margin_top + 7 * (cell_size + cell_spacing) + 35

    # Construir SVG
    svg_parts = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        '<style>',
        '  text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 10px; fill: #8b949e; }',
        '  .month { font-size: 10px; }',
        '  .day { font-size: 9px; }',
        '  .title { font-size: 12px; font-weight: 600; fill: #c9d1d9; }',
        '</style>',
        f'<rect width="{width}" height="{height}" fill="#0d1117" rx="6"/>',
    ]

    # Labels dos dias
    day_labels = ['', 'Mon', '', 'Wed', '', 'Fri', '']
    for i, label in enumerate(day_labels):
        if label:
            y = margin_top + i * (cell_size + cell_spacing) + cell_size - 1
            svg_parts.append(f'<text x="5" y="{y}" class="day">{label}</text>')

    # Células e labels de mês
    current_date = start_date
    week_idx = 0
    last_month = -1

    while current_date <= today:
        day_of_week = current_date.weekday()
        day_idx = (day_of_week + 1) % 7  # Domingo = 0

        if day_of_week == 6 and current_date != start_date:
            week_idx += 1

        date_str = current_date.strftime('%Y-%m-%d')
        seconds = daily_data.get(date_str, 0)
        level = get_level(seconds)
        color = colors[level]

        x = margin_left + week_idx * (cell_size + cell_spacing)
        y = margin_top + day_idx * (cell_size + cell_spacing)

        hours = seconds / 3600
        tooltip = f"{date_str}: {hours:.1f}h" if seconds > 0 else f"{date_str}: No coding"

        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
            f'fill="{color}" rx="2" data-date="{date_str}">'
            f'<title>{tooltip}</title></rect>'
        )

        # Label do mês (apenas no início de cada mês)
        if current_date.month != last_month and day_idx == 0:
            month_name = MONTHS[current_date.month - 1]
            svg_parts.append(f'<text x="{x}" y="12" class="month">{month_name}</text>')
            last_month = current_date.month

        current_date += timedelta(days=1)

    # Legenda
    legend_x = width - 110
    legend_y = height - 18
    svg_parts.append(f'<text x="{legend_x - 30}" y="{legend_y + 8}" class="day">Less</text>')

    for i, color in enumerate(colors):
        lx = legend_x + i * (cell_size + 2)
        svg_parts.append(f'<rect x="{lx}" y="{legend_y}" width="{cell_size}" height="{cell_size}" fill="{color}" rx="2"/>')

    svg_parts.append(f'<text x="{legend_x + 5 * (cell_size + 2) + 5}" y="{legend_y + 8}" class="day">More</text>')

    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)


def generate_wakatime_section(stats: dict, all_time: dict = None) -> str:
    """Gera toda a seção do WakaTime para o README"""

    lines = []

    # Tempo de coding
    total_time = stats.get('human_readable_total', 'N/A')
    daily_avg = stats.get('human_readable_daily_average', 'N/A')

    lines.append("#### ⏰ Tempo de Coding")
    lines.append("")
    lines.append("```text")
    lines.append(f"Total (últimos 7 dias)    : {total_time}")
    lines.append(f"Média diária              : {daily_avg}")

    if all_time:
        all_time_text = all_time.get('text', 'N/A')
        lines.append(f"Total desde o início      : {all_time_text}")

    lines.append("```")
    lines.append("")

    # Linguagens
    languages = stats.get('languages', [])
    if languages:
        lines.append("#### 💻 Linguagens Mais Usadas (últimos 7 dias)")
        lines.append("")
        lines.append("```text")

        for lang in languages[:5]:
            name = lang.get('name', 'Unknown')
            percent = lang.get('percent', 0)
            time_text = lang.get('text', '0 mins')

            bar_length = 20
            filled = int(bar_length * percent / 100)
            bar = '█' * filled + '░' * (bar_length - filled)

            name_padded = name.ljust(15)
            lines.append(f"{name_padded} {bar} {percent:5.1f}% ({time_text})")

        lines.append("```")
        lines.append("")

    return '\n'.join(lines)


def update_readme(readme_content: str, new_section: str,
                  start_marker: str, end_marker: str) -> str:
    """Atualiza uma seção específica do README entre marcadores"""

    pattern = re.compile(
        f"{re.escape(start_marker)}.*?{re.escape(end_marker)}",
        re.DOTALL
    )

    new_content = f"{start_marker}\n{new_section}\n{end_marker}"

    if pattern.search(readme_content):
        return pattern.sub(new_content, readme_content)
    else:
        logger.warning("Marcadores não encontrados. Adicionando seção ao final.")
        return readme_content + f"\n\n{new_content}"


def fetch_historical_data(api: WakaTimeAPI, history: HistoryManager, days_back: int = 14) -> dict:
    """
    Busca dados históricos do WakaTime e faz merge com o histórico existente.
    Por padrão busca os últimos 14 dias para garantir sobreposição.
    """
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

    logger.info(f"Buscando dados de {start_date} até {end_date}...")

    summaries = api.get_summaries(start_date, end_date)

    if not summaries:
        logger.warning("Não foi possível obter dados históricos")
        return history.get_activity()

    # Processar dados da API
    new_data = {}
    for day in summaries:
        date = day.get('range', {}).get('date', '')
        total_seconds = day.get('grand_total', {}).get('total_seconds', 0)
        if date:
            new_data[date] = total_seconds

    # Fazer merge com histórico existente
    history.merge_activity(new_data)
    history.save()

    return history.get_activity()


def main():
    """Função principal"""

    api_key = os.getenv('WAKATIME_API_KEY')
    if not api_key:
        logger.error("WAKATIME_API_KEY não encontrada nas variáveis de ambiente.")
        return False

    readme_path = os.getenv('README_PATH', 'README.md')
    svg_path = os.getenv('SVG_PATH', 'wakatime_activity.svg')

    logger.info("Iniciando atualização do README com dados do WakaTime...")

    # Inicializar cliente da API e gerenciador de histórico
    api = WakaTimeAPI(api_key)
    history = HistoryManager(HISTORY_FILE)

    # Mostrar estatísticas do histórico existente
    hist_stats = history.get_stats()
    logger.info(f"Histórico existente: {hist_stats['total_days']} dias, {hist_stats['total_hours']}h total")

    # Buscar estatísticas dos últimos 7 dias
    logger.info("Buscando estatísticas dos últimos 7 dias...")
    stats = api.get_stats("last_7_days")
    if not stats:
        logger.error("Não foi possível obter estatísticas do WakaTime.")
        return False

    # Buscar tempo total
    logger.info("Buscando tempo total de coding...")
    all_time = api.get_all_time_since_today()

    # Buscar dados históricos e fazer merge
    logger.info("Atualizando histórico de atividade...")
    daily_data = fetch_historical_data(api, history, days_back=14)

    # Mostrar estatísticas atualizadas
    hist_stats = history.get_stats()
    logger.info(f"Histórico atualizado: {hist_stats['total_days']} dias, {hist_stats['total_hours']}h total")

    # Gerar SVG do gráfico de atividade
    logger.info("Gerando gráfico de atividade SVG...")
    svg_content = generate_activity_svg(daily_data, weeks=52)

    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    logger.info(f"Gráfico SVG salvo em {svg_path}")

    # Gerar seção do WakaTime
    wakatime_section = generate_wakatime_section(stats, all_time)

    # Ler README atual
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
    except FileNotFoundError:
        logger.error(f"README não encontrado em {readme_path}")
        return False

    # Atualizar seção de estatísticas
    readme_content = update_readme(
        readme_content,
        wakatime_section,
        START_MARKER,
        END_MARKER
    )

    # Atualizar referência ao gráfico
    graph_section = f'<p align="center">\n  <img src="{svg_path}" alt="WakaTime Activity Graph" />\n</p>'
    readme_content = update_readme(
        readme_content,
        graph_section,
        GRAPH_START,
        GRAPH_END
    )

    # Salvar README
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    logger.info("README.md atualizado com sucesso!")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
