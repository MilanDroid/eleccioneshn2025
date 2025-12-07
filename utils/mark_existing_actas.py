#!/usr/bin/env python3
"""
Script to mark existing downloaded actas as not needing download.
This scans the /actas directory and updates the corresponding mesas.json files
to set needs_download=false for actas that already exist locally.
"""

import json
import os
from pathlib import Path

def parse_acta_filename(filename):
    """
    Parse acta filename to extract components.
    Format: DEPT-MUNI-ZONA-CENTRO-MESA.pdf
    Returns: (dept_code, muni_code, zona_code, centro_code, mesa_num)
    """
    if not filename.endswith('.pdf'):
        return None

    # Remove .pdf extension
    base = filename[:-4]
    parts = base.split('-')

    if len(parts) != 5:
        return None

    return tuple(parts)

def find_mesas_file(mesas_data_dir, dept_code, muni_code, centro_code):
    """
    Find the mesas.json file for a given department/municipio/centro.
    Returns the Path to the mesas.json file or None if not found.
    """
    # We need to search for the centro folder that starts with centro_code
    dept_folder = None
    for folder in mesas_data_dir.iterdir():
        if folder.is_dir():
            # Try to find matching department by scanning for muni codes
            # This is approximate - we'll search all dept folders
            dept_folder = folder
            for muni_folder in dept_folder.iterdir():
                if not muni_folder.is_dir():
                    continue

                for centro_folder in muni_folder.iterdir():
                    if not centro_folder.is_dir():
                        continue

                    # Check if centro folder starts with the centro_code
                    if centro_folder.name.startswith(f"{centro_code}_"):
                        mesas_file = centro_folder / "mesas.json"
                        if mesas_file.exists():
                            return mesas_file

    return None

def mark_existing_actas():
    """
    Main function to mark existing actas as not needing download.
    """
    base_dir = Path("..")
    actas_dir = base_dir / "actas"
    mesas_data_dir = base_dir / "mesas_data"

    if not actas_dir.exists():
        print("Error: actas directory not found!")
        return

    if not mesas_data_dir.exists():
        print("Error: mesas_data directory not found!")
        return

    # Get all PDF files in actas directory
    acta_files = list(actas_dir.glob("*.pdf"))
    print(f"Found {len(acta_files)} existing acta files")

    # Create a set of all downloaded mesa identifiers for fast lookup
    # Format: "DEPT-MUNI-ZONA-CENTRO-MESA"
    downloaded_actas = set()
    for acta_file in acta_files:
        parsed = parse_acta_filename(acta_file.name)
        if not parsed:
            print(f"Warning: Could not parse filename: {acta_file.name}")
            continue

        dept_code, muni_code, zona_code, centro_code, mesa_num = parsed
        # Create identifier matching the mesas.json structure
        acta_id = f"{dept_code}-{muni_code}-{zona_code}-{centro_code}-{mesa_num}"
        downloaded_actas.add(acta_id)

    print(f"Created lookup set with {len(downloaded_actas)} acta identifiers")
    print(f"\nProcessing all mesas.json files...")

    # Statistics
    stats = {
        'total_mesas': 0,
        'mesas_marked_false': 0,
        'mesas_already_false': 0,
        'mesas_left_true': 0,
        'files_updated': 0
    }

    # Load municipios data to get department codes
    try:
        with open("municipios_data.json", "r", encoding="utf-8") as f:
            municipios_data = json.load(f)
    except:
        print("Warning: Could not load municipios_data.json")
        municipios_data = {}

    # Process all mesas.json files
    for dept_folder in mesas_data_dir.iterdir():
        if not dept_folder.is_dir():
            continue

        dept_name = dept_folder.name

        # Get department code
        dept_code = None
        for dept_name_lookup, dept_info in municipios_data.items():
            if dept_name_lookup == dept_name:
                dept_code = dept_info["codigo"]
                break

        if not dept_code:
            continue

        for muni_folder in dept_folder.iterdir():
            if not muni_folder.is_dir():
                continue

            for centro_folder in muni_folder.iterdir():
                if not centro_folder.is_dir():
                    continue

                # Extract centro code from folder name
                folder_parts = centro_folder.name.split('_', 1)
                if len(folder_parts) < 2:
                    continue

                centro_code = folder_parts[0]

                mesas_file = centro_folder / "mesas.json"
                if not mesas_file.exists():
                    continue

                # Load and process mesas.json
                try:
                    with open(mesas_file, 'r', encoding='utf-8') as f:
                        mesas_list = json.load(f)

                    # Get zona code from first mesa if available
                    zona_code = None
                    if mesas_list and 'id_informacion_mesa_corporacion' in mesas_list[0]:
                        mesa_id = mesas_list[0]['id_informacion_mesa_corporacion']
                        if len(mesa_id) >= 8:
                            zona_code = mesa_id[5:7]

                    if not zona_code:
                        continue

                    # Get municipio code from municipios_data
                    muni_name = muni_folder.name
                    muni_code = None
                    for dept_info_name, dept_info_data in municipios_data.items():
                        if dept_info_data['codigo'] == dept_code:
                            for muni in dept_info_data.get('municipios', []):
                                if muni['municipio'] == muni_name:
                                    muni_code = muni['id_municipio']
                                    break
                            break

                    if not muni_code:
                        continue

                    # Check each mesa and update needs_download flag
                    updated = False
                    for mesa in mesas_list:
                        stats['total_mesas'] += 1
                        mesa_num = str(mesa.get('numero'))

                        # Create identifier for this mesa
                        acta_id = f"{dept_code}-{muni_code}-{zona_code}-{centro_code}-{mesa_num}"

                        # Check if this acta exists
                        if acta_id in downloaded_actas:
                            # Acta exists, should be marked as false
                            if mesa.get('needs_download') != False:
                                mesa['needs_download'] = False
                                updated = True
                                stats['mesas_marked_false'] += 1
                            else:
                                stats['mesas_already_false'] += 1
                        else:
                            # Acta doesn't exist, should be true
                            stats['mesas_left_true'] += 1

                    # Save updated mesas.json if changes were made
                    if updated:
                        with open(mesas_file, 'w', encoding='utf-8') as f:
                            json.dump(mesas_list, f, ensure_ascii=False, indent=2)
                        stats['files_updated'] += 1

                except Exception as e:
                    print(f"  Error processing {mesas_file}: {e}")

    # Print summary
    print("\n" + "="*60)
    print("Summary:")
    print(f"  Total mesas processed: {stats['total_mesas']}")
    print(f"  Mesas marked as needs_download=false: {stats['mesas_marked_false']}")
    print(f"  Mesas already false: {stats['mesas_already_false']}")
    print(f"  Mesas left as true (not downloaded): {stats['mesas_left_true']}")
    print(f"  Total with needs_download=false: {stats['mesas_marked_false'] + stats['mesas_already_false']}")
    print(f"  Mesas.json files updated: {stats['files_updated']}")
    print("="*60)

if __name__ == "__main__":
    mark_existing_actas()
