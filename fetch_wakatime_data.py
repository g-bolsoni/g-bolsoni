#!/usr/bin/env python3
"""
WakaTime README Stats Updater
Atualiza o README.md com estatísticas do WakaTime incluindo:
- Tempo total de coding
- Linguagens mais usadas
- Gráfico de atividade estilo GitHub
"""

import requests
import os
import logging
import re
import base64
from datetime import datetime, timedelta
from collections import defaultdict

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

# Cores para o gráfico (níveis de intensidade)
ACTIVITY_LEVELS = ['▒', '░', '▓', '█', '█']  # Caracteres para diferentes níveis
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


class WakaTimeAPI:
    """Cliente para a API do WakaTime"""

    BASE_URL = "https://wakatime.com/api/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Basic {base64.b64encode(api_key.encode()).decode()}"
        }

    def _request(self, endpoint: str, params: dict = None) -> dict:
        """Faz uma requisição à API do WakaTime"""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
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
        })
        return data.get('data', []) if data else []

    def get_all_time_since_today(self) -> dict:
        """Obtém tempo total de coding desde sempre"""
        data = self._request("users/current/all_time_since_today")
        return data.get('data') if data else None


def generate_activity_graph(daily_data: dict, weeks: int = 52) -> str:
    """
    Gera um gráfico de atividade estilo GitHub contribution graph

    Args:
        daily_data: Dicionário com datas como chave e segundos como valor
        weeks: Número de semanas para mostrar

    Returns:
        String com o gráfico formatado
    """
    today = datetime.now().date()

    # Encontrar o domingo mais próximo para começar
    days_since_sunday = (today.weekday() + 1) % 7
    end_date = today
    start_date = today - timedelta(days=(weeks * 7) + days_since_sunday)

    # Calcular níveis de atividade
    max_seconds = max(daily_data.values()) if daily_data else 1

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

    # Criar grid de atividade
    grid = []
    current_date = start_date
    week_data = []

    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        seconds = daily_data.get(date_str, 0)
        level = get_level(seconds)
        week_data.append((current_date, level, seconds))

        if current_date.weekday() == 6:  # Domingo
            grid.append(week_data)
            week_data = []

        current_date += timedelta(days=1)

    if week_data:
        grid.append(week_data)

    # Gerar cabeçalho de meses
    month_header = "       "
    last_month = -1
    for week_idx, week in enumerate(grid):
        if week:
            month = week[0][0].month
            if month != last_month:
                month_header += f" {MONTHS[month - 1]}"
                last_month = month
            else:
                month_header += "   "

    # Gerar linhas do gráfico (apenas Mon, Wed, Fri para simplificar)
    lines = [month_header]

    day_indices = [0, 2, 4]  # Mon, Wed, Fri
    day_labels = ['Mon', 'Wed', 'Fri']

    for idx, day_idx in enumerate(day_indices):
        line = f"  {day_labels[idx]} "
        for week in grid:
            if day_idx < len(week):
                _, level, _ = week[day_idx]
                if level == 0:
                    line += "⬜"
                elif level == 1:
                    line += "🟦"
                elif level == 2:
                    line += "🟦"
                elif level == 3:
                    line += "🟩"
                else:
                    line += "🟩"
            else:
                line += "  "
        lines.append(line)

    # Legenda
    lines.append("")
    lines.append("  Less ⬜🟦🟩 More")

    return "\n".join(lines)


def generate_activity_svg(daily_data: dict, weeks: int = 52) -> str:
    """
    Gera um SVG do gráfico de atividade
    """
    today = datetime.now().date()

    # Configurações do SVG
    cell_size = 11
    cell_spacing = 3
    margin_left = 40
    margin_top = 20

    # Cores (estilo GitHub dark)
    colors = ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353']

    days_since_sunday = (today.weekday() + 1) % 7
    start_date = today - timedelta(days=(weeks * 7) + days_since_sunday - 1)

    # Calcular níveis
    max_seconds = max(daily_data.values()) if daily_data else 1

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
    width = margin_left + (weeks + 1) * (cell_size + cell_spacing) + 20
    height = margin_top + 7 * (cell_size + cell_spacing) + 40

    # Construir SVG
    svg_parts = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        '<style>',
        '  text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 10px; fill: #8b949e; }',
        '  .month { font-size: 10px; }',
        '  .day { font-size: 9px; }',
        '</style>',
        f'<rect width="{width}" height="{height}" fill="#0d1117" rx="6"/>',
    ]

    # Labels dos dias
    day_labels = ['', 'Mon', '', 'Wed', '', 'Fri', '']
    for i, label in enumerate(day_labels):
        if label:
            y = margin_top + i * (cell_size + cell_spacing) + cell_size - 1
            svg_parts.append(f'<text x="5" y="{y}" class="day">{label}</text>')

    # Células
    current_date = start_date
    week_idx = 0

    while current_date <= today:
        day_of_week = current_date.weekday()
        day_idx = (day_of_week + 1) % 7  # Domingo = 0

        if day_of_week == 6:  # Novo domingo, nova semana
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

        # Label do mês
        if current_date.day <= 7 and day_idx == 0:
            month_name = MONTHS[current_date.month - 1]
            svg_parts.append(f'<text x="{x}" y="12" class="month">{month_name}</text>')

        current_date += timedelta(days=1)

    # Legenda
    legend_x = width - 120
    legend_y = height - 20
    svg_parts.append(f'<text x="{legend_x - 30}" y="{legend_y + 9}" class="day">Less</text>')

    for i, color in enumerate(colors):
        lx = legend_x + i * (cell_size + 2)
        svg_parts.append(f'<rect x="{lx}" y="{legend_y}" width="{cell_size}" height="{cell_size}" fill="{color}" rx="2"/>')

    svg_parts.append(f'<text x="{legend_x + 5 * (cell_size + 2) + 5}" y="{legend_y + 9}" class="day">More</text>')

    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)


def generate_languages_section(languages: list, limit: int = 5) -> str:
    """Gera a seção de linguagens mais usadas com barras de progresso"""
    if not languages:
        return "Nenhuma linguagem registrada"

    lines = []

    # Pegar top linguagens
    top_languages = languages[:limit]

    for lang in top_languages:
        name = lang.get('name', 'Unknown')
        percent = lang.get('percent', 0)
        time_text = lang.get('text', '0 mins')

        # Criar barra de progresso
        bar_length = 25
        filled = int(bar_length * percent / 100)
        bar = '█' * filled + '░' * (bar_length - filled)

        lines.append(f"**{name}**")
        lines.append(f"`{bar}` {percent:.1f}% ({time_text})")
        lines.append("")

    return '\n'.join(lines)


def format_time(total_seconds: int) -> str:
    """Formata segundos em formato legível"""
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours >= 24:
        days = hours // 24
        hours = hours % 24
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


def generate_wakatime_section(stats: dict, daily_data: dict, all_time: dict = None) -> str:
    """Gera toda a seção do WakaTime para o README"""

    lines = []

    # Tempo de coding
    total_time = stats.get('human_readable_total', 'N/A')
    daily_avg = stats.get('human_readable_daily_average', 'N/A')

    lines.append("#### ⏰ Tempo de Coding")
    lines.append("")
    lines.append(f"```text")
    lines.append(f"Total (últimos 7 dias)    : {total_time}")
    lines.append(f"Média diária              : {daily_avg}")

    if all_time:
        all_time_text = all_time.get('text', 'N/A')
        lines.append(f"Total desde o início      : {all_time_text}")

    lines.append(f"```")
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

            # Criar barra de progresso ASCII
            bar_length = 20
            filled = int(bar_length * percent / 100)
            bar = '█' * filled + '░' * (bar_length - filled)

            # Formatar linha
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
        # Se não encontrar os marcadores, adiciona no final
        logger.warning(f"Marcadores não encontrados. Adicionando seção ao final.")
        return readme_content + f"\n\n{new_content}"


def main():
    """Função principal"""

    api_key = os.getenv('WAKATIME_API_KEY')
    if not api_key:
        logger.error("WAKATIME_API_KEY não encontrada nas variáveis de ambiente.")
        return False

    readme_path = os.getenv('README_PATH', 'README.md')

    logger.info("Iniciando atualização do README com dados do WakaTime...")

    # Inicializar cliente da API
    api = WakaTimeAPI(api_key)

    # Buscar estatísticas
    logger.info("Buscando estatísticas dos últimos 7 dias...")
    stats = api.get_stats("last_7_days")
    if not stats:
        logger.error("Não foi possível obter estatísticas do WakaTime.")
        return False

    # Buscar tempo total
    logger.info("Buscando tempo total de coding...")
    all_time = api.get_all_time_since_today()

    # Gerar seção do WakaTime (sem gráfico de atividade por enquanto - muito lento)
    wakatime_section = generate_wakatime_section(stats, {}, all_time)

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

    # Salvar README
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    logger.info("README.md atualizado com sucesso!")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
