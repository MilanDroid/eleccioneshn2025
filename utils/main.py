import requests
import json
import os
import time
from datetime import datetime
from typing import Dict, Any
from constants import DEPARTAMENTOS, PARTIDOS, PARTIDOS_LOGOS, CANDIDATOS, CANDIDATOS_IMAGENES

def fetch_election_results(depto: str) -> Dict[Any, Any]:
    """
    Fetch election results for a specific department.

    Args:
        depto: Department code (00-18)

    Returns:
        JSON response from the API
    """
    url = "https://resultadosgenerales2025-api.cne.hn/esc/v1/presentacion-resultados"

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,es;q=0.8",
        "authorization": "Bearer null",
        "content-type": "application/json",
        "dnt": "1",
        "origin": "https://resultadosgenerales2025.cne.hn",
        "priority": "u=1, i",
        "referer": "https://resultadosgenerales2025.cne.hn/",
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    }

    payload = {
        "codigos": [],
        "tipco": "01",
        "depto": depto,
        "comuna": "00",
        "mcpio": "000",
        "zona": "",
        "pesto": "",
        "mesa": 0
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for department {depto}: {e}")
        return None

def fetch_actas_validas(depto: str) -> Dict[Any, Any]:
    """
    Fetch valid vote papers (actas validas) data for a specific department.

    Args:
        depto: Department code (00-18)

    Returns:
        JSON response from the API with actas data
    """
    url = "https://resultadosgenerales2025-api.cne.hn/esc/v1/presentacion-resultados/actas-validas"

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,es;q=0.8",
        "authorization": "Bearer null",
        "content-type": "application/json",
        "dnt": "1",
        "origin": "https://resultadosgenerales2025.cne.hn",
        "priority": "u=1, i",
        "referer": "https://resultadosgenerales2025.cne.hn/",
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    }

    payload = {
        "codigos": [],
        "tipco": "01",
        "depto": depto,
        "comuna": "00",
        "mcpio": "000",
        "zona": "",
        "pesto": "",
        "mesa": 0
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching actas data for department {depto}: {e}")
        return None

def save_results(results: Dict[Any, Any], actas_data: Dict[Any, Any], depto: str, timestamp: str) -> None:
    """
    Save election results to a JSON file organized by timestamp.
    Saves optimized candidate data with only essential fields: cddto_nombres, parpo_nombre, votos.

    Args:
        results: Election results data
        actas_data: Valid vote papers (actas) data
        depto: Department code
        timestamp: Timestamp for organizing results
    """
    # Create directory structure: results/YYYY-MM-DD_HH-MM-SS/
    results_dir = os.path.join("results", timestamp)
    os.makedirs(results_dir, exist_ok=True)

    # Get department name
    depto_name = DEPARTAMENTOS.get(depto, f"UNKNOWN_{depto}")

    # Extract only essential candidate fields
    optimized_candidatos = []
    for candidato in results.get("candidatos", []):
        optimized_candidatos.append({
            "cddto_nombres": candidato.get("cddto_nombres"),
            "parpo_nombre": candidato.get("parpo_nombre"),
            "votos": candidato.get("votos")
        })

    # Save complete results with actas data above fecha_corte
    complete_results = {
        "actas": actas_data,
        "fecha_corte": results.get("fecha_corte"),
        "depto_code": depto,
        "depto_name": depto_name,
        "candidatos": optimized_candidatos
    }

    # Save file using department name
    filename = f"{depto_name}.json"
    filepath = os.path.join(results_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(complete_results, f, ensure_ascii=False, indent=2)

    print(f"Saved results for {depto_name} to {filepath}")

def get_total_votes(results: Dict[Any, Any]) -> int:
    """
    Calculate total votes from all candidates.

    Args:
        results: Election results data

    Returns:
        Total number of votes
    """
    total = 0
    for candidato in results.get("candidatos", []):
        total += candidato.get("votos", 0)
    return total

def get_last_saved_total_votes() -> int:
    """
    Get the total votes from the most recent saved TODOS results.

    Returns:
        Total votes from last saved results, or 0 if none exist
    """
    # Check if results_metadata.json exists
    metadata_path = "results_metadata.json"
    if not os.path.exists(metadata_path):
        return 0

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        latest_date = metadata.get("latest_date")
        if not latest_date:
            return 0

        # Load TODOS.json from the latest results
        todos_path = os.path.join("results", latest_date, "TODOS.json")
        if not os.path.exists(todos_path):
            return 0

        with open(todos_path, "r", encoding="utf-8") as f:
            todos_data = json.load(f)

        total = 0
        for candidato in todos_data.get("candidatos", []):
            total += candidato.get("votos", 0)

        return total
    except Exception as e:
        print(f"Error reading last saved results: {e}")
        return 0

def fetch_all_departments() -> None:
    """
    Fetch election results for all departments defined in DEPARTAMENTOS.
    Only saves if the total votes for TODOS has changed.
    """
    print("Fetching election results...")
    print("=" * 60)

    # First, fetch department 00 (TODOS) to check total votes
    print("\nFetching general results (department 00 - TODOS)...")
    results = fetch_election_results("00")

    if not results:
        print("⚠️  Failed to fetch initial results. Will retry in next cycle.")
        print("=" * 60)
        return

    # Calculate current total votes
    current_total_votes = get_total_votes(results)
    print(f"\nCurrent total votes: {current_total_votes:,}")

    # Get last saved total votes
    last_saved_total_votes = get_last_saved_total_votes()
    print(f"Last saved total votes: {last_saved_total_votes:,}")

    # Check if total votes have changed
    if current_total_votes == last_saved_total_votes:
        print(f"\n⚠️  Total votes unchanged ({current_total_votes:,})")
        print("   Skipping fetch to avoid duplicates.")
        print("=" * 60)
        return

    # Total votes changed - save new results
    print(f"\n✓ Total votes changed! ({last_saved_total_votes:,} → {current_total_votes:,})")

    # Create timestamp for this snapshot
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results_dir = os.path.join("results", timestamp)

    print(f"✓ Saving new results to: {results_dir}")
    print("=" * 60)

    # Fetch and save department 00 actas
    print("\nFetching actas data for TODOS (00)...")
    actas_00 = fetch_actas_validas("00")
    if actas_00:
        save_results(results, actas_00, "00", timestamp)
    else:
        print("⚠️  Warning: Failed to fetch actas for TODOS. Saving without actas data.")
        save_results(results, {}, "00", timestamp)

    # Fetch all other departments from DEPARTAMENTOS (excluding 00 which we already fetched)
    for depto_code in DEPARTAMENTOS.keys():
        if depto_code == "00":
            continue

        depto_name = DEPARTAMENTOS[depto_code]
        print(f"\nFetching results for {depto_name} ({depto_code})...")
        results = fetch_election_results(depto_code)
        if results:
            # Fetch actas for this department
            print(f"Fetching actas data for {depto_name} ({depto_code})...")
            actas = fetch_actas_validas(depto_code)
            if actas:
                save_results(results, actas, depto_code, timestamp)
            else:
                print(f"⚠️  Warning: Failed to fetch actas for {depto_name}. Saving without actas data.")
                save_results(results, {}, depto_code, timestamp)

    print("\n" + "=" * 60)
    print("Finished fetching all election results!")

    # Generate metadata for web page
    print("\nGenerating metadata for web page...")
    os.system("python3 generate_metadata.py")

    # Commit and push changes to GitHub
    print("\nCommitting and pushing changes to GitHub...")
    print("=" * 60)

    # Add results directory and metadata file
    os.system("git add results/ results_metadata.json")

    # Create commit with timestamp and vote count
    commit_message = f"Nuevo corte"
    os.system(f'git commit -m "{commit_message}"')

    # Push to GitHub
    push_result = os.system("git push origin main")

    if push_result == 0:
        print("✓ Successfully pushed changes to GitHub!")
    else:
        print("⚠️  Warning: Failed to push changes to GitHub. Check your connection and credentials.")

    print("=" * 60)

if __name__ == "__main__":
    print("Starting continuous election results monitoring...")
    print("Process will run every 90 seconds. Press Ctrl+C to stop.")
    print("=" * 60)

    try:
        while True:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] Starting fetch cycle...")

            fetch_all_departments()

            print(f"\n[{current_time}] Fetch cycle complete. Waiting 90 seconds...")
            print("=" * 60)
            time.sleep(90)
    except KeyboardInterrupt:
        print("\n\nStopping election results monitoring. Goodbye!")
        print("=" * 60)