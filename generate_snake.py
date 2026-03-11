#!/usr/bin/env python3
"""
Gera uma animação SVG de snake usando dados de atividade do WakaTime.
A cobra "come" os quadrados de atividade do gráfico.
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

HISTORY_FILE = "wakatime_history.json"
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def load_history() -> dict:
    """Carrega histórico do WakaTime"""
    path = Path(HISTORY_FILE)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('daily_activity', {})
    return {}


def generate_snake_svg(daily_data: dict, weeks: int = 52) -> str:
    """
    Gera um SVG animado com snake comendo os quadrados de atividade
    """
    today = datetime.now().date()

    # Configurações
    cell_size = 10
    cell_spacing = 3
    cell_total = cell_size + cell_spacing
    margin_left = 35
    margin_top = 25

    # Cores
    colors = ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353']
    snake_color = '#9be9a8'

    # Calcular data inicial
    days_since_sunday = (today.weekday() + 1) % 7
    start_date = today - timedelta(days=(weeks * 7) + days_since_sunday - 1)

    # Calcular níveis
    values = [v for v in daily_data.values() if v > 0]
    if values:
        sorted_values = sorted(values)
        p90_idx = int(len(sorted_values) * 0.9)
        max_seconds = sorted_values[p90_idx] if p90_idx < len(sorted_values) else sorted_values[-1]
        max_seconds = max(max_seconds, 3600)
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
    width = margin_left + (weeks + 1) * cell_total + 30
    height = margin_top + 7 * cell_total + 40

    # Construir grid de células e coletar células com atividade
    cells = []
    active_cells = []
    current_date = start_date
    week_idx = 0
    last_month = -1
    month_labels = []

    while current_date <= today:
        day_of_week = current_date.weekday()
        day_idx = (day_of_week + 1) % 7

        if day_of_week == 6 and current_date != start_date:
            week_idx += 1

        date_str = current_date.strftime('%Y-%m-%d')
        seconds = daily_data.get(date_str, 0)
        level = get_level(seconds)

        x = margin_left + week_idx * cell_total
        y = margin_top + day_idx * cell_total

        cells.append({
            'x': x, 'y': y,
            'level': level,
            'date': date_str,
            'seconds': seconds,
            'week': week_idx,
            'day': day_idx
        })

        if level > 0:
            active_cells.append(len(cells) - 1)

        # Labels de mês
        if current_date.month != last_month and day_idx == 0:
            month_labels.append({
                'x': x,
                'name': MONTHS[current_date.month - 1]
            })
            last_month = current_date.month

        current_date += timedelta(days=1)

    # Calcular caminho da snake (visitar células ativas em padrão serpentina)
    def sort_cells_snake_pattern(indices):
        """Ordena células em padrão serpentina (esquerda-direita, depois direita-esquerda)"""
        if not indices:
            return []

        # Agrupar por semana
        by_week = {}
        for idx in indices:
            cell = cells[idx]
            week = cell['week']
            if week not in by_week:
                by_week[week] = []
            by_week[week].append(idx)

        # Ordenar cada semana por dia
        for week in by_week:
            by_week[week].sort(key=lambda i: cells[i]['day'])

        # Construir caminho serpentina
        result = []
        weeks_sorted = sorted(by_week.keys())
        reverse = False

        for week in weeks_sorted:
            week_cells = by_week[week]
            if reverse:
                week_cells = week_cells[::-1]
            result.extend(week_cells)
            reverse = not reverse

        return result

    snake_path = sort_cells_snake_pattern(active_cells)

    # Duração total da animação
    total_duration = 10  # segundos

    # Início do SVG
    svg_parts = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        '<defs>',
        '  <style>',
        '    text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 10px; fill: #8b949e; }',
        '    .month { font-size: 10px; }',
        '    .day { font-size: 9px; }',
        '  </style>',
        '</defs>',
        f'<rect width="{width}" height="{height}" fill="#0d1117" rx="6"/>',
    ]

    # Labels dos dias
    day_labels = ['', 'Mon', '', 'Wed', '', 'Fri', '']
    for i, label in enumerate(day_labels):
        if label:
            y = margin_top + i * cell_total + cell_size - 1
            svg_parts.append(f'<text x="5" y="{y}" class="day">{label}</text>')

    # Labels dos meses
    for ml in month_labels:
        svg_parts.append(f'<text x="{ml["x"]}" y="12" class="month">{ml["name"]}</text>')

    # Células com animação de fade-out quando snake passa
    for i, cell in enumerate(cells):
        x, y = cell['x'], cell['y']
        level = cell['level']
        color = colors[level]

        # Verificar se esta célula está no caminho da snake
        if i in snake_path:
            path_idx = snake_path.index(i)
            # Tempo quando a snake alcança esta célula
            eat_time = (path_idx / len(snake_path)) * total_duration if snake_path else 0

            # Célula original que desaparece
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{color}" rx="2">'
                f'  <animate attributeName="fill" values="{color};{colors[0]}" '
                f'           begin="{eat_time:.2f}s" dur="0.3s" fill="freeze"/>'
                f'</rect>'
            )
        else:
            # Célula sem atividade (permanece escura)
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{color}" rx="2"/>'
            )

    # Gerar snake
    if snake_path:
        snake_length = 5  # Número de segmentos

        # Snake head
        head_positions_x = []
        head_positions_y = []

        for idx in snake_path:
            cell = cells[idx]
            head_positions_x.append(str(cell['x'] + cell_size // 2))
            head_positions_y.append(str(cell['y'] + cell_size // 2))

        # Adicionar posição final (fora da tela)
        head_positions_x.append(str(width + 20))
        head_positions_y.append(head_positions_y[-1] if head_positions_y else str(height // 2))

        # Keyframes para movimento
        key_times = ';'.join([f"{i / len(head_positions_x):.3f}" for i in range(len(head_positions_x))])
        values_x = ';'.join(head_positions_x)
        values_y = ';'.join(head_positions_y)

        # Cabeça da snake
        svg_parts.append(f'''
        <circle r="{cell_size // 2}" fill="{snake_color}">
            <animate attributeName="cx" values="{values_x}" keyTimes="{key_times}" dur="{total_duration}s" fill="freeze"/>
            <animate attributeName="cy" values="{values_y}" keyTimes="{key_times}" dur="{total_duration}s" fill="freeze"/>
        </circle>
        ''')

        # Corpo da snake (segmentos que seguem a cabeça com delay)
        for seg in range(1, snake_length):
            delay = seg * 0.15
            opacity = 1 - (seg * 0.15)
            size = cell_size // 2 - seg
            if size < 2:
                size = 2

            svg_parts.append(f'''
            <circle r="{size}" fill="{snake_color}" opacity="{opacity:.2f}">
                <animate attributeName="cx" values="{values_x}" keyTimes="{key_times}" dur="{total_duration}s" begin="{delay}s" fill="freeze"/>
                <animate attributeName="cy" values="{values_y}" keyTimes="{key_times}" dur="{total_duration}s" begin="{delay}s" fill="freeze"/>
            </circle>
            ''')

        # Olhos da snake
        svg_parts.append(f'''
        <g>
            <circle r="2" fill="#161b22">
                <animate attributeName="cx" values="{';'.join([str(int(x) - 2) for x in head_positions_x])}" keyTimes="{key_times}" dur="{total_duration}s" fill="freeze"/>
                <animate attributeName="cy" values="{';'.join([str(int(y) - 2) for y in head_positions_y])}" keyTimes="{key_times}" dur="{total_duration}s" fill="freeze"/>
            </circle>
            <circle r="2" fill="#161b22">
                <animate attributeName="cx" values="{';'.join([str(int(x) + 2) for x in head_positions_x])}" keyTimes="{key_times}" dur="{total_duration}s" fill="freeze"/>
                <animate attributeName="cy" values="{';'.join([str(int(y) - 2) for y in head_positions_y])}" keyTimes="{key_times}" dur="{total_duration}s" fill="freeze"/>
            </circle>
        </g>
        ''')

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


def main():
    print("🐍 Gerando animação de snake com dados do WakaTime...")

    daily_data = load_history()

    if not daily_data:
        print("❌ Nenhum dado encontrado em wakatime_history.json")
        print("   Execute primeiro: python3 fetch_wakatime_data.py")
        return False

    print(f"📊 {len(daily_data)} dias de dados carregados")

    svg_content = generate_snake_svg(daily_data, weeks=52)

    output_file = "wakatime_snake.svg"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    print(f"✅ Animação salva em: {output_file}")
    return True


if __name__ == "__main__":
    main()
