import requests
import json
from utils.constants import DEPARTAMENTOS

def fetch_municipios():
    """
    Fetch municipios for each department from the CNE API.
    Stores the result in a JSON file with departments as properties.
    """
    base_url = "https://resultadosgenerales2025-api.cne.hn/esc/v1/actas-documentos"

    # Dictionary to store all department data
    departamentos_data = {}

    # Iterate through each department (excluding "TODOS" and "VOTO EN EL EXTERIOR" which might not have municipios)
    for dept_code, dept_name in DEPARTAMENTOS.items():
        # Skip "TODOS" and "VOTO EN EL EXTERIOR" as they don't have municipios
        if dept_code in ["00", "20"]:
            print(f"Skipping {dept_name} (code: {dept_code})")
            continue

        print(f"Fetching municipios for {dept_name} (code: {dept_code})...")

        # Construct the URL: /01/{dept_code}/municipios
        url = f"{base_url}/01/{dept_code}/municipios"

        try:
            response = requests.get(url)
            response.raise_for_status()

            municipios = response.json()

            # Store the data with the department name as key
            departamentos_data[dept_name] = {
                "codigo": dept_code,
                "municipios": municipios
            }

            print(f"  ✓ Found {len(municipios)} municipios")

        except requests.exceptions.RequestException as e:
            print(f"  ✗ Error fetching data for {dept_name}: {e}")
            departamentos_data[dept_name] = {
                "codigo": dept_code,
                "municipios": [],
                "error": str(e)
            }

    # Save to JSON file
    output_file = "municipios_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(departamentos_data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Data saved to {output_file}")
    print(f"Total departments processed: {len(departamentos_data)}")

if __name__ == "__main__":
    fetch_municipios()
