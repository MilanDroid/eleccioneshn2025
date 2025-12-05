import requests
import json
import time
import os
from pathlib import Path

def get_zona_code(zona_name):
    """Convert zona name to code"""
    return "01" if zona_name == "URBANA" else "02"

def sanitize_folder_name(name):
    """Sanitize folder names by removing invalid characters"""
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()

def fetch_mesas():
    """
    Fetch mesas (voting tables) for each centro in each zona.
    Uses the centros_data.json and municipios_data.json files as input.
    Creates folder structure: mesas_data/{department}/{municipio}/{centro}/mesas.json
    """
    base_url = "https://resultadosgenerales2025-api.cne.hn/esc/v1/actas-documentos"

    # Load municipios data (to get municipio codes)
    with open("municipios_data.json", "r", encoding="utf-8") as f:
        municipios_data = json.load(f)

    # Load centros data
    with open("centros_data.json", "r", encoding="utf-8") as f:
        centros_data = json.load(f)

    # Create a lookup dictionary for municipio codes
    municipio_codes = {}
    for dept_name, dept_info in municipios_data.items():
        dept_code = dept_info["codigo"]
        if dept_code not in municipio_codes:
            municipio_codes[dept_code] = {}
        for municipio in dept_info["municipios"]:
            municipio_codes[dept_code][municipio["municipio"]] = municipio["id_municipio"]

    # Create base directory for mesas data
    base_dir = Path("mesas_data")
    base_dir.mkdir(exist_ok=True)

    # Statistics
    total_municipios = 0
    total_zonas = 0
    total_centros = 0
    total_mesas = 0
    errors = []

    # Iterate through each department
    for dept_name, dept_info in centros_data.items():
        print(f"\nProcessing {dept_name}...")

        # Get department code from municipios_data
        dept_code = None
        for dept_name_lookup, dept_lookup_info in municipios_data.items():
            if dept_name_lookup == dept_name:
                dept_code = dept_lookup_info["codigo"]
                break

        if not dept_code:
            print(f"  ✗ Could not find department code for {dept_name}")
            continue

        print(f"  Department code: {dept_code}")

        # Create department folder
        dept_folder = base_dir / sanitize_folder_name(dept_name)
        dept_folder.mkdir(exist_ok=True)

        # Iterate through each municipio in the department
        for municipio_info in dept_info["municipios"]:
            municipio_name = municipio_info["municipio"]
            municipio_zonas = municipio_info["zonas"]

            # Get municipio code
            municipio_code = municipio_codes.get(dept_code, {}).get(municipio_name)
            if not municipio_code:
                print(f"  ✗ Could not find code for {municipio_name}")
                continue

            total_municipios += 1
            print(f"  Processing {municipio_name} (code: {municipio_code})...")

            # Create municipio folder
            municipio_folder = dept_folder / sanitize_folder_name(municipio_name)
            municipio_folder.mkdir(exist_ok=True)

            # Iterate through each zona in the municipio
            for zona_info in municipio_zonas:
                zona_name = zona_info["zona"]
                zona_code = get_zona_code(zona_name)
                centros = zona_info["centros"]
                total_zonas += 1

                print(f"    Processing {zona_name} zone with {len(centros)} centros...")

                # Iterate through each centro in the zona
                for centro in centros:
                    centro_id = centro["id_puesto"]
                    centro_name = centro["puesto"]
                    total_centros += 1

                    # Create centro folder
                    centro_folder_name = f"{centro_id}_{sanitize_folder_name(centro_name)}"
                    centro_folder = municipio_folder / centro_folder_name
                    centro_folder.mkdir(exist_ok=True)

                    print(f"      Fetching mesas for centro {centro_id}...", end=" ")

                    # Construct the URL: /01/{dept_code}/{municipio_code}/{zona_code}/{centro_id}/mesas
                    url = f"{base_url}/01/{dept_code}/{municipio_code}/{zona_code}/{centro_id}/mesas"

                    try:
                        response = requests.get(url)
                        response.raise_for_status()

                        mesas_list = response.json()

                        # Save mesas to JSON file
                        mesas_file = centro_folder / "mesas.json"
                        with open(mesas_file, "w", encoding="utf-8") as f:
                            json.dump(mesas_list, f, ensure_ascii=False, indent=2)

                        total_mesas += len(mesas_list)
                        print(f"✓ {len(mesas_list)} mesas")

                        # Small delay to avoid overwhelming the API
                        time.sleep(0.05)

                    except requests.exceptions.RequestException as e:
                        error_msg = f"{dept_name} > {municipio_name} > {zona_name} > {centro_name}: {str(e)}"
                        errors.append(error_msg)
                        print(f"✗ Error: {e}")

                        # Create empty mesas file on error
                        mesas_file = centro_folder / "mesas.json"
                        with open(mesas_file, "w", encoding="utf-8") as f:
                            json.dump([], f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✓ Data saved to {base_dir} folder")
    print(f"Total departments: {len(centros_data)}")
    print(f"Total municipios processed: {total_municipios}")
    print(f"Total zonas processed: {total_zonas}")
    print(f"Total centros processed: {total_centros}")
    print(f"Total mesas fetched: {total_mesas}")

    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")

if __name__ == "__main__":
    fetch_mesas()
