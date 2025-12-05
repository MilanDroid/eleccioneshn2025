import requests
import json
import time

def fetch_zonas():
    """
    Fetch zonas for each municipio in each department from the CNE API.
    Uses the municipios_data.json file as input.
    Stores the result in a compact JSON file structure.
    Format: {department_name: {municipios: [{municipio: name, zonas: [zone_names]}]}}
    """
    base_url = "https://resultadosgenerales2025-api.cne.hn/esc/v1/actas-documentos"

    # Load municipios data
    with open("municipios_data.json", "r", encoding="utf-8") as f:
        municipios_data = json.load(f)

    # Dictionary to store all data with zonas
    zonas_data = {}
    total_municipios = 0
    total_zonas = 0
    errors = []

    # Iterate through each department
    for dept_name, dept_info in municipios_data.items():
        dept_code = dept_info["codigo"]
        municipios = dept_info.get("municipios", [])

        print(f"\nProcessing {dept_name} (code: {dept_code})...")
        print(f"  Total municipios: {len(municipios)}")

        # Initialize department data with simplified structure
        zonas_data[dept_name] = {
            "municipios": []
        }

        # Iterate through each municipio in the department
        for municipio in municipios:
            municipio_code = municipio["id_municipio"]
            municipio_name = municipio["municipio"]
            total_municipios += 1

            print(f"  Fetching zonas for {municipio_name} (code: {municipio_code})...", end=" ")

            # Construct the URL: /01/{dept_code}/{municipio_code}/00/zonas
            url = f"{base_url}/01/{dept_code}/{municipio_code}/00/zonas"

            try:
                response = requests.get(url)
                response.raise_for_status()

                zonas = response.json()

                # Extract just the zone names (URBANA or RURAL)
                zona_names = [zona["zona"] for zona in zonas]

                # Store the municipio data with simplified zonas
                municipio_data = {
                    "municipio": municipio_name,
                    "zonas": zona_names
                }

                zonas_data[dept_name]["municipios"].append(municipio_data)
                total_zonas += len(zona_names)

                print(f"✓ {len(zona_names)} zonas")

                # Small delay to avoid overwhelming the API
                time.sleep(0.1)

            except requests.exceptions.RequestException as e:
                error_msg = f"{dept_name} > {municipio_name}: {str(e)}"
                errors.append(error_msg)
                print(f"✗ Error: {e}")

                # Store municipio with empty zonas on error
                municipio_data = {
                    "municipio": municipio_name,
                    "zonas": []
                }
                zonas_data[dept_name]["municipios"].append(municipio_data)

    # Save to JSON file
    output_file = "zonas_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(zonas_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✓ Data saved to {output_file}")
    print(f"Total departments: {len(zonas_data)}")
    print(f"Total municipios processed: {total_municipios}")
    print(f"Total zonas fetched: {total_zonas}")

    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")

if __name__ == "__main__":
    fetch_zonas()
