import requests
import json
import time

def get_zona_code(zona_name):
    """Convert zona name to code"""
    return "01" if zona_name == "URBANA" else "02"

def fetch_centros():
    """
    Fetch centros (voting centers) for each zona in each municipio.
    Uses the zonas_data.json and municipios_data.json files as input.
    Stores the result in a compact JSON file structure with IDs.
    Format: {department_name: {municipios: [{municipio: name, zonas: [{zona: name, centros: [{id_puesto, puesto}]}]}]}}
    """
    base_url = "https://resultadosgenerales2025-api.cne.hn/esc/v1/actas-documentos"

    # Load municipios data (to get municipio codes)
    with open("municipios_data.json", "r", encoding="utf-8") as f:
        municipios_data = json.load(f)

    # Load zonas data
    with open("zonas_data.json", "r", encoding="utf-8") as f:
        zonas_data = json.load(f)

    # Create a lookup dictionary for municipio codes
    municipio_codes = {}
    for dept_name, dept_info in municipios_data.items():
        dept_code = dept_info["codigo"]
        if dept_code not in municipio_codes:
            municipio_codes[dept_code] = {}
        for municipio in dept_info["municipios"]:
            municipio_codes[dept_code][municipio["municipio"]] = municipio["id_municipio"]

    # Dictionary to store all data with centros
    centros_data = {}
    total_municipios = 0
    total_zonas = 0
    total_centros = 0
    errors = []

    # Iterate through each department
    for dept_name, dept_info in zonas_data.items():
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

        # Initialize department data
        centros_data[dept_name] = {
            "municipios": []
        }

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

            # Initialize municipio data
            municipio_data = {
                "municipio": municipio_name,
                "zonas": []
            }

            # Iterate through each zona in the municipio
            for zona_name in municipio_zonas:
                zona_code = get_zona_code(zona_name)
                total_zonas += 1

                print(f"    Fetching centros for {zona_name} (code: {zona_code})...", end=" ")

                # Construct the URL: /01/{dept_code}/{municipio_code}/{zona_code}/puestos
                url = f"{base_url}/01/{dept_code}/{municipio_code}/{zona_code}/puestos"

                try:
                    response = requests.get(url)
                    response.raise_for_status()

                    centros_list = response.json()

                    # Extract id_puesto and puesto for each centro
                    centros = [
                        {
                            "id_puesto": centro["id_puesto"],
                            "puesto": centro["puesto"]
                        }
                        for centro in centros_list
                    ]

                    # Store the zona data with centros
                    zona_data = {
                        "zona": zona_name,
                        "centros": centros
                    }

                    municipio_data["zonas"].append(zona_data)
                    total_centros += len(centros)

                    print(f"✓ {len(centros)} centros")

                    # Small delay to avoid overwhelming the API
                    time.sleep(0.1)

                except requests.exceptions.RequestException as e:
                    error_msg = f"{dept_name} > {municipio_name} > {zona_name}: {str(e)}"
                    errors.append(error_msg)
                    print(f"✗ Error: {e}")

                    # Store zona with empty centros on error
                    zona_data = {
                        "zona": zona_name,
                        "centros": []
                    }
                    municipio_data["zonas"].append(zona_data)

            centros_data[dept_name]["municipios"].append(municipio_data)

    # Save to JSON file
    output_file = "centros_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(centros_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✓ Data saved to {output_file}")
    print(f"Total departments: {len(centros_data)}")
    print(f"Total municipios processed: {total_municipios}")
    print(f"Total zonas processed: {total_zonas}")
    print(f"Total centros fetched: {total_centros}")

    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")

if __name__ == "__main__":
    fetch_centros()
