#!/usr/bin/env python3
"""
Validation script for extracted acta JSON files
Checks for completeness and data consistency
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def validate_acta(json_data: Dict, filename: str) -> Tuple[bool, List[str]]:
    """
    Validate a single acta JSON file
    Returns (is_valid, list_of_issues)
    """
    issues = []

    # Check required top-level keys
    required_keys = ['archivo', 'metadata', 'papeletas', 'votos']
    for key in required_keys:
        if key not in json_data:
            issues.append(f"Missing required key: {key}")

    # Check papeletas section
    papeletas_fields = [
        'recibidas_segun_acta_apertura',
        'no_utilizadas_sobrantes',
        'utilizadas',
        'ciudadanos_que_votaron',
        'miembros_jrv',
        'custodios',
        'total_votantes'
    ]

    papeletas = json_data.get('papeletas', {})
    missing_papeletas = [f for f in papeletas_fields if f not in papeletas]
    if missing_papeletas:
        issues.append(f"Missing papeletas fields: {', '.join(missing_papeletas)}")

    # Check votos section
    votos_fields = [
        'partido_nacional_democrata_honduras',
        'libre',
        'partido_innovacion_unidad_social_democratica',
        'partido_liberal_honduras',
        'partido_nacional_honduras',
        'votos_en_blanco',
        'votos_nulos',
        'gran_total'
    ]

    votos = json_data.get('votos', {})
    missing_votos = [f for f in votos_fields if f not in votos]
    if missing_votos:
        issues.append(f"Missing votos fields: {', '.join(missing_votos)}")

    # Check data structure (numero + letras)
    for field_name, field_data in papeletas.items():
        if not isinstance(field_data, dict):
            issues.append(f"Papeletas.{field_name} is not a dict")
            continue
        if 'numero' not in field_data or 'letras' not in field_data:
            issues.append(f"Papeletas.{field_name} missing 'numero' or 'letras'")

    for field_name, field_data in votos.items():
        if not isinstance(field_data, dict):
            issues.append(f"Votos.{field_name} is not a dict")
            continue
        if 'numero' not in field_data or 'letras' not in field_data:
            issues.append(f"Votos.{field_name} missing 'numero' or 'letras'")

    # Validate arithmetic if all fields present
    if not missing_papeletas:
        try:
            recibidas = int(papeletas['recibidas_segun_acta_apertura']['numero'])
            no_utilizadas = int(papeletas['no_utilizadas_sobrantes']['numero'])
            utilizadas = int(papeletas['utilizadas']['numero'])

            if recibidas != (no_utilizadas + utilizadas):
                issues.append(f"Arithmetic error: recibidas ({recibidas}) != no_utilizadas ({no_utilizadas}) + utilizadas ({utilizadas})")
        except (ValueError, KeyError) as e:
            # Can't validate if numbers are not valid
            pass

    if not missing_votos:
        try:
            # Sum all party votes + blank + null
            total = 0
            for field in votos_fields[:-1]:  # Exclude gran_total
                if field in votos:
                    total += int(votos[field]['numero'])

            gran_total = int(votos['gran_total']['numero'])
            if total != gran_total:
                issues.append(f"Vote sum error: sum of votes ({total}) != gran_total ({gran_total})")
        except (ValueError, KeyError) as e:
            # Can't validate if numbers are not valid
            pass

    is_valid = len(issues) == 0
    return is_valid, issues

def validate_all(json_dir: str):
    """
    Validate all JSON files in a directory
    """
    json_path = Path(json_dir)

    if not json_path.exists():
        print(f"Error: Directory {json_dir} does not exist")
        sys.exit(1)

    json_files = sorted(list(json_path.glob('*.json')))

    if not json_files:
        print(f"No JSON files found in {json_dir}")
        return

    print(f"Validating {len(json_files)} JSON files...")
    print("="*60)

    valid_count = 0
    invalid_count = 0

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            is_valid, issues = validate_acta(data, json_file.name)

            if is_valid:
                print(f"✓ {json_file.name}")
                valid_count += 1
            else:
                print(f"✗ {json_file.name}")
                for issue in issues:
                    print(f"  - {issue}")
                invalid_count += 1
        except json.JSONDecodeError as e:
            print(f"✗ {json_file.name}")
            print(f"  - JSON parse error: {e}")
            invalid_count += 1
        except Exception as e:
            print(f"✗ {json_file.name}")
            print(f"  - Unexpected error: {e}")
            invalid_count += 1

    print("\n" + "="*60)
    print("Validation Summary:")
    print(f"  Total files: {len(json_files)}")
    print(f"  Valid: {valid_count}")
    print(f"  Invalid: {invalid_count}")

    if invalid_count == 0:
        print("\n✓ All files are valid!")
    else:
        print(f"\n⚠ {invalid_count} files have issues")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate extracted acta JSON files'
    )

    parser.add_argument(
        'json_dir',
        help='Directory containing JSON files to validate',
        default='actas_json',
        nargs='?'
    )

    args = parser.parse_args()

    validate_all(args.json_dir)

if __name__ == '__main__':
    main()
