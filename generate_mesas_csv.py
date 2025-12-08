#!/usr/bin/env python3
"""
Script to generate a CSV file from all mesas.json files in the directory structure.
Directory structure: Departamento/Municipio/Centro/mesas.json
"""

import os
import json
import csv
from pathlib import Path


def find_mesas_json_files(base_path):
    """
    Recursively find all mesas.json files in the directory structure.
    Returns list of tuples: (departamento, municipio, centro, file_path)
    """
    mesas_files = []
    base_path = Path(base_path)

    # Walk through the directory structure
    for departamento_dir in base_path.iterdir():
        if not departamento_dir.is_dir():
            continue

        departamento = departamento_dir.name

        for municipio_dir in departamento_dir.iterdir():
            if not municipio_dir.is_dir():
                continue

            municipio = municipio_dir.name

            for centro_dir in municipio_dir.iterdir():
                if not centro_dir.is_dir():
                    continue

                centro = centro_dir.name

                # Look for mesas.json in this centro directory
                mesas_file = centro_dir / "mesas.json"
                if mesas_file.exists() and mesas_file.is_file():
                    mesas_files.append((departamento, municipio, centro, mesas_file))

    return mesas_files


def generate_csv(base_path, output_file):
    """
    Generate CSV file from all mesas.json files.
    """
    # Define CSV columns
    fieldnames = [
        "Departamento",
        "Municipio",
        "Centro",
        "Mesa#",
        "Publicada",
        "Escrutado",
        "Digitalizado",
        "Mesa ID",
        "Etiquetas",
        "Link"
    ]

    # Find all mesas.json files
    print(f"Scanning directory: {base_path}")
    mesas_files = find_mesas_json_files(base_path)
    print(f"Found {len(mesas_files)} mesas.json files")

    # Open CSV file for writing
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        total_mesas = 0

        # Process each mesas.json file
        for departamento, municipio, centro, file_path in mesas_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    mesas_data = json.load(f)

                # Process each mesa in the array
                for mesa in mesas_data:
                    # Extract etiquetas as comma-separated string
                    etiquetas = ', '.join(mesa.get('etiquetas', []))

                    # Create CSV row
                    row = {
                        "Departamento": departamento,
                        "Municipio": municipio,
                        "Centro": centro,
                        "Mesa#": mesa.get('numero', ''),
                        "Publicada": mesa.get('publicada', ''),
                        "Escrutado": mesa.get('escrutado', ''),
                        "Digitalizado": mesa.get('digitalizado', ''),
                        "Mesa ID": mesa.get('id_informacion_mesa_corporacion', ''),
                        "Etiquetas": etiquetas,
                        "Link": mesa.get('nombre_archivo', '')
                    }

                    writer.writerow(row)
                    total_mesas += 1

            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

        print(f"Successfully processed {total_mesas} mesas")
        print(f"CSV file created: {output_file}")


if __name__ == "__main__":
    # Define paths
    base_path = "../eleccioneshn2025Actualizaciones/mesas_data"
    output_file = "mesas_output.csv"

    # Generate CSV
    generate_csv(base_path, output_file)
