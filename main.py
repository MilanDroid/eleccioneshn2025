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
    url = "https://api-publicacion-nacional.elecciones-hnd.grupoasd.xyz/esc/v1/presentacion-resultados"

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,es;q=0.8",
        "authorization": "Bearer null",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "dnt": "1",
        "origin": "https://resultadosgenerales2025.cne.hn",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://resultadosgenerales2025.cne.hn/",
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
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

def save_results(results: Dict[Any, Any], depto: str, fecha_corte: str) -> None:
    """
    Save election results to a JSON file organized by fecha_corte.
    Only saves essential fields: votos, cddto_nombres, and parpo_nombre.

    Args:
        results: Election results data
        depto: Department code
        fecha_corte: Cut-off date for results
    """
    # Create directory structure: results/YYYY-MM-DD_HH-MM-SS/
    fecha_corte_clean = fecha_corte.replace(":", "-").replace(" ", "_").replace(".0", "")
    results_dir = os.path.join("results", fecha_corte_clean)
    os.makedirs(results_dir, exist_ok=True)

    # Get department name
    depto_name = DEPARTAMENTOS.get(depto, f"UNKNOWN_{depto}")

    # Extract only the essential fields
    simplified_results = {
        "fecha_corte": results.get("fecha_corte"),
        "depto_code": depto,
        "depto_name": depto_name,
        "candidatos": []
    }

    for candidato in results.get("candidatos", []):
        simplified_results["candidatos"].append({
            "cddto_nombres": candidato.get("cddto_nombres"),
            "parpo_nombre": candidato.get("parpo_nombre"),
            "votos": candidato.get("votos")
        })

    # Save file using department name
    filename = f"{depto_name}.json"
    filepath = os.path.join(results_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(simplified_results, f, ensure_ascii=False, indent=2)

    print(f"Saved results for {depto_name} to {filepath}")

def fetch_all_departments() -> None:
    """
    Fetch election results for all departments defined in DEPARTAMENTOS.
    Only saves if the fecha_corte from the API response is new.
    """
    print("Fetching election results...")
    print("=" * 60)

    # First, fetch department 00 to get the actual fecha_corte from response
    print("\nFetching general results (department 00)...")
    results = fetch_election_results("00")

    if not results:
        print("⚠️  Failed to fetch initial results. Will retry in next cycle.")
        print("=" * 60)
        return

    # Get the actual fecha_corte from the API response
    actual_fecha_corte = results.get("fecha_corte")
    if not actual_fecha_corte:
        print("⚠️  Error: No fecha_corte in response. Will retry in next cycle.")
        print("=" * 60)
        return

    print(f"\nAPI returned fecha_corte: {actual_fecha_corte}")

    # Check if this fecha_corte already has saved results
    fecha_corte_clean = actual_fecha_corte.replace(":", "-").replace(" ", "_").replace(".0", "")
    results_dir = os.path.join("results", fecha_corte_clean)

    if os.path.exists(results_dir):
        print(f"\n⚠️  Results for fecha_corte '{actual_fecha_corte}' already exist!")
        print(f"   Directory: {results_dir}")
        print("   Skipping fetch to avoid duplicates.")
        print("=" * 60)
        return

    print(f"\n✓ New fecha_corte detected. Saving results to: {results_dir}")
    print("=" * 60)

    # Save department 00
    save_results(results, "00", actual_fecha_corte)

    # Fetch all other departments from DEPARTAMENTOS (excluding 00 which we already fetched)
    for depto_code in DEPARTAMENTOS.keys():
        if depto_code == "00":
            continue

        depto_name = DEPARTAMENTOS[depto_code]
        print(f"\nFetching results for {depto_name} ({depto_code})...")
        results = fetch_election_results(depto_code)
        if results:
            save_results(results, depto_code, actual_fecha_corte)

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

    # Create commit with fecha_corte timestamp
    commit_message = f"Update election results - {actual_fecha_corte}"
    os.system(f'git commit -m "{commit_message}"')

    # Push to GitHub
    push_result = os.system("git push")

    if push_result == 0:
        print("✓ Successfully pushed changes to GitHub!")
    else:
        print("⚠️  Warning: Failed to push changes to GitHub. Check your connection and credentials.")

    print("=" * 60)

if __name__ == "__main__":
    print("Starting continuous election results monitoring...")
    print("Process will run every 60 seconds. Press Ctrl+C to stop.")
    print("=" * 60)

    try:
        while True:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] Starting fetch cycle...")

            fetch_all_departments()

            print(f"\n[{current_time}] Fetch cycle complete. Waiting 60 seconds...")
            print("=" * 60)
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n\nStopping election results monitoring. Goodbye!")
        print("=" * 60)