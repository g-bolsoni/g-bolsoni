#!/usr/bin/env python3
"""
Gera uma animação SVG de snake usando dados de atividade do WakaTime.
A cobra se move pelo gráfico de atividade em loop contínuo.
"""

import json
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
    Gera um SVG animado com snake se movendo pelo gráfico de atividade
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

    # Calcular caminho da snake em padrão serpentina por TODAS as células
    def get_all_cells_snake_pattern():
        """Retorna todas as células em padrão serpentina"""
        result = []
        max_week = max(c['week'] for c in cells) if cells else 0
        
        for week in range(max_week + 1):
            week_cells = [i for i, c in enumerate(cells) if c['week'] == week]
            week_cells.sort(key=lambda i: cells[i]['day'])
            
            if week % 2 == 1:  # Semanas ímpares: de baixo pra cima
                week_cells = week_cells[::-1]
            
            result.extend(week_cells)
        
        return result

    all_cells_path = get_all_cells_snake_pattern()

    # Duração e configuração da animação
    total_duration = 10  # segundos para percorrer o gráfico
    
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
    day_labels_text = ['', 'Mon', '', 'Wed', '', 'Fri', '']
    for i, label in enumerate(day_labels_text):
        if label:
            y = margin_top + i * cell_total + cell_size - 1
            svg_parts.append(f'<text x="5" y="{y}" class="day">{label}</text>')

    # Labels dos meses
    for ml in month_labels:
        svg_parts.append(f'<text x="{ml["x"]}" y="12" class="month">{ml["name"]}</text>')

    # Desenhar TODAS as células (gráfico estático)
    for cell in cells:
        x, y = cell['x'], cell['y']
        level = cell['level']
        color = colors[level]
        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{color}" rx="2"/>'
        )

    # Gerar posições da snake
    if all_cells_path:
        # Posições do caminho
        positions = []
        for idx in all_cells_path:
            cell = cells[idx]
            positions.append((cell['x'] + cell_size // 2, cell['y'] + cell_size // 2))
        
        # Adicionar posição inicial (fora da tela à esquerda)
        start_x = -20
        start_y = positions[0][1] if positions else margin_top + cell_size // 2
        
        # Adicionar posição final (fora da tela à direita)
        end_x = width + 20
        end_y = positions[-1][1] if positions else margin_top + cell_size // 2
        
        # Construir caminho completo: entrada -> percurso -> saída -> (pausa) -> volta à entrada
        full_path = [(start_x, start_y)] + positions + [(end_x, end_y)]
        
        # Gerar valores para animação
        values_x = ';'.join([str(p[0]) for p in full_path])
        values_y = ';'.join([str(p[1]) for p in full_path])
        
        # KeyTimes distribuídos uniformemente
        n_points = len(full_path)
        key_times = ';'.join([f"{i / (n_points - 1):.4f}" for i in range(n_points)])
        
        # Snake body segments
        snake_segments = 8
        segment_delay = 0.08  # segundos entre segmentos
        
        # Cabeça da snake (maior, com olhos)
        svg_parts.append(f'''
        <g>
            <!-- Cabeça -->
            <circle r="{cell_size // 2 + 1}" fill="{snake_color}">
                <animate attributeName="cx" values="{values_x}" keyTimes="{key_times}" 
                         dur="{total_duration}s" repeatCount="indefinite" calcMode="linear"/>
                <animate attributeName="cy" values="{values_y}" keyTimes="{key_times}" 
                         dur="{total_duration}s" repeatCount="indefinite" calcMode="linear"/>
            </circle>
            <!-- Olho esquerdo -->
            <circle r="2" fill="#161b22">
                <animate attributeName="cx" values="{';'.join([str(p[0] - 2) for p in full_path])}" keyTimes="{key_times}" 
                         dur="{total_duration}s" repeatCount="indefinite" calcMode="linear"/>
                <animate attributeName="cy" values="{';'.join([str(p[1] - 2) for p in full_path])}" keyTimes="{key_times}" 
                         dur="{total_duration}s" repeatCount="indefinite" calcMode="linear"/>
            </circle>
            <!-- Olho direito -->
            <circle r="2" fill="#161b22">
                <animate attributeName="cx" values="{';'.join([str(p[0] + 2) for p in full_path])}" keyTimes="{key_times}" 
                         dur="{total_duration}s" repeatCount="indefinite" calcMode="linear"/>
                <animate attributeName="cy" values="{';'.join([str(p[1] - 2) for p in full_path])}" keyTimes="{key_times}" 
                         dur="{total_duration}s" repeatCount="indefinite" calcMode="linear"/>
            </circle>
        </g>
        ''')
        
        # Segmentos do corpo (seguem a cabeça com delay)
        for seg in range(1, snake_segments):
            delay = seg * segment_delay
            size = max(cell_size // 2 + 1 - seg, 2)
            opacity = max(1.0 - (seg * 0.1), 0.3)
            
            svg_parts.append(f'''
            <circle r="{size}" fill="{snake_color}" opacity="{opacity:.2f}">
                <animate attributeName="cx" values="{values_x}" keyTimes="{key_times}" 
                         dur="{total_duration}s" begin="{delay:.2f}s" repeatCount="indefinite" calcMode="linear"/>
                <animate attributeName="cy" values="{values_y}" keyTimes="{key_times}" 
                         dur="{total_duration}s" begin="{delay:.2f}s" repeatCount="indefinite" calcMode="linear"/>
            </circle>
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
