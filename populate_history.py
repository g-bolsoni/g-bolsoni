#!/usr/bin/env python3
"""
Script para popular o histórico do WakaTime com dados antigos.
Execute uma vez para buscar dados históricos.

Uso:
    WAKATIME_API_KEY="sua_chave" python3 populate_history.py --months 12
"""

import requests
import os
import json
import base64
import argparse
import time
from datetime import datetime, timedelta
from pathlib import Path

HISTORY_FILE = "wakatime_history.json"
BASE_URL = "https://wakatime.com/api/v1"


def get_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Basic {base64.b64encode(api_key.encode()).decode()}"
    }


def fetch_summaries(api_key: str, start: str, end: str) -> list:
    """Busca resumos diários entre duas datas"""
    headers = get_headers(api_key)
    url = f"{BASE_URL}/users/current/summaries"

    try:
        response = requests.get(url, headers=headers, params={
            "start": start,
            "end": end
        }, timeout=120)
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.exceptions.RequestException as e:
        print(f"  Erro ao buscar {start} até {end}: {e}")
        return []


def load_history() -> dict:
    """Carrega histórico existente"""
    path = Path(HISTORY_FILE)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "daily_activity": {},
        "last_updated": None,
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        }
    }


def save_history(data: dict) -> None:
    """Salva histórico"""
    data["last_updated"] = datetime.now().isoformat()
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def populate_history(api_key: str, months: int = 12, chunk_days: int = 30):
    """
    Popula o histórico buscando dados em chunks para evitar timeout.

    Args:
        api_key: Chave da API do WakaTime
        months: Número de meses para buscar
        chunk_days: Dias por requisição (máx ~30 para evitar timeout)
    """
    print(f"🚀 Populando histórico com dados dos últimos {months} meses...")
    print()

    history = load_history()
    existing_days = len(history.get("daily_activity", {}))
    print(f"📊 Histórico existente: {existing_days} dias")

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=months * 30)

    total_days = (end_date - start_date).days
    total_chunks = (total_days // chunk_days) + 1

    print(f"📅 Período: {start_date} até {end_date} ({total_days} dias)")
    print(f"📦 Dividido em {total_chunks} requisições de ~{chunk_days} dias")
    print()

    all_data = {}
    current_start = start_date
    chunk_num = 0

    while current_start < end_date:
        chunk_num += 1
        current_end = min(current_start + timedelta(days=chunk_days - 1), end_date)

        start_str = current_start.strftime('%Y-%m-%d')
        end_str = current_end.strftime('%Y-%m-%d')

        print(f"  [{chunk_num}/{total_chunks}] Buscando {start_str} até {end_str}...", end=" ", flush=True)

        summaries = fetch_summaries(api_key, start_str, end_str)

        if summaries:
            for day in summaries:
                date = day.get('range', {}).get('date', '')
                total_seconds = day.get('grand_total', {}).get('total_seconds', 0)
                if date:
                    all_data[date] = total_seconds
            print(f"✅ {len(summaries)} dias")
        else:
            print("❌ Falhou")

        current_start = current_end + timedelta(days=1)

        # Pequena pausa entre requisições para não sobrecarregar a API
        time.sleep(0.5)

    print()

    # Merge com histórico existente
    added = 0
    for date, seconds in all_data.items():
        if date not in history["daily_activity"]:
            added += 1
        history["daily_activity"][date] = seconds

    save_history(history)

    total_days = len(history["daily_activity"])
    total_hours = sum(history["daily_activity"].values()) / 3600

    print(f"✅ Concluído!")
    print(f"   - Novos dias adicionados: {added}")
    print(f"   - Total de dias no histórico: {total_days}")
    print(f"   - Total de horas registradas: {total_hours:.1f}h")
    print()
    print(f"💾 Salvo em: {HISTORY_FILE}")
    print()
    print("Agora execute o script principal para gerar o gráfico:")
    print("  python3 fetch_wakatime_data.py")


def main():
    parser = argparse.ArgumentParser(
        description='Popula o histórico do WakaTime com dados antigos'
    )
    parser.add_argument(
        '--months', '-m',
        type=int,
        default=12,
        help='Número de meses para buscar (padrão: 12)'
    )
    parser.add_argument(
        '--chunk-days', '-c',
        type=int,
        default=30,
        help='Dias por requisição (padrão: 30)'
    )

    args = parser.parse_args()

    api_key = os.getenv('WAKATIME_API_KEY')
    if not api_key:
        print("❌ Erro: WAKATIME_API_KEY não encontrada.")
        print()
        print("Execute assim:")
        print('  WAKATIME_API_KEY="sua_chave" python3 populate_history.py')
        exit(1)

    populate_history(api_key, months=args.months, chunk_days=args.chunk_days)


if __name__ == "__main__":
    main()
