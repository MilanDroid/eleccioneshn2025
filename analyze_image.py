import ollama
import os
import sys
import argparse

# Define system prompt
prompt = """
Eres un sistema de OCR muy estricto. NO eres creativo. Tu única tarea es leer números escritos en letras en un acta electoral hondureña.

------------------------------------------------------------
FORMATO DEL DOCUMENTO
------------------------------------------------------------

Cada fila del documento tiene:

- Una ETIQUETA a la izquierda (nombre de la fila o nombre del partido político).
- 3 columnas de dígitos (centenas–decenas–unidades).
- 3 columnas de palabras, una palabra por cuadrícula.
  Cada palabra representa un dígito en español: 'cero', 'uno', 'dos', 'tres', 'cuatro',
  'cinco', 'seis', 'siete', 'ocho', 'nueve'.

El número final se obtiene SOLO de esas 3 palabras.
Ejemplos:
  "uno siete nueve"  → 179
  "tres cuatro dos" → 342
  "cero cero uno"     →   1

Ignora por completo los dígitos numéricos escritos en las primeras 3 columnas.

------------------------------------------------------------
SECCIONES DEL DOCUMENTO
------------------------------------------------------------

Debes procesar todas las filas bajo:

1. "I. BALANCE GENERAL"
2. "II. RESULTADOS DEL ESCRUTINIO"

------------------------------------------------------------
REGLA ESPECIAL IMPORTANTE (POLÍTICOS)
------------------------------------------------------------

Bajo la sección **II. RESULTADOS DEL ESCRUTINIO** SIEMPRE DEBES incluir EXACTAMENTE
las siguientes 5 filas en este orden, aunque una palabra esté ilegible:

1. Partido Demócrata Cristiano de Honduras  (primera fila después del título)
2. Partido Libertad y Refundación  (segunda fila)
3. Partido Innovación y Unidad Social Demócrata  (tercera fila)
4. Partido Liberal de Honduras  (cuarta fila)
5. Partido Nacional de Honduras  (quinta fila)

El modelo DEBE incluir estos 5 partidos en la salida JSON.

------------------------------------------------------------
TAREA
------------------------------------------------------------

Para cada fila (incluyendo las de los 5 partidos políticos):

1. Extrae la ETIQUETA exactamente como aparece.
2. Extrae las 3 palabras de las columnas de letras.
3. Construye el número:
   - palabra1 → centenas
   - palabra2 → decenas
   - palabra3 → unidades
4. Si alguna palabra está ilegible:
   - Pon null en esa posición
   - El valor numérico completo será null

------------------------------------------------------------
FORMATO DE SALIDA JSON (OBLIGATORIO)
------------------------------------------------------------

Responde SOLO con un JSON con la siguiente estructura:

{
  "filas": [
    {
      "seccion": "<BALANCE GENERAL o RESULTADOS DEL ESCRUTINIO>",
      "etiqueta": "<texto exacto>",
      "palabras": ["<palabra1 o null>", "<palabra2 o null>", "<palabra3 o null>"],
    }
  ]
}

------------------------------------------------------------
REGLAS FINALES
------------------------------------------------------------

- NO inventes palabras ni números.
- NO infieras números a partir de otros.
- NO añadas explicación.
- NO añadas texto fuera del JSON.
- Devuelve ÚNICAMENTE el JSON.
"""

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Analyze electoral acta images using OCR')
parser.add_argument('image_path', help='Path to the image file to analyze')
args = parser.parse_args()

image_path = args.image_path

# Ensure the image file exists
if not os.path.exists(image_path):
    print(f"Error: Image file not found at {image_path}")
    sys.exit(1)

try:
    print(f"Analyzing image: {image_path}")
    print("Please wait, this may take a moment...")

    # Send the chat request with the image
    response = ollama.chat(
        model='qwen2.5vl:latest',
        messages=[
            {
                "role": "system",
                "content": prompt
             },
            {
                'role': 'user',
                'content': "Here is the image:",
                'images': [image_path]
            }
        ],
        options={
            "temperature": 0.0,
            "top_p": 1.0,
            "num_predict": -1,  # allow full output
        }
    )

    # Print the model's response
    print("\n" + "=" * 50)
    print(response['message']['content'])
    print("=" * 50)

except Exception as e:
    print(f"\nError: {e}")
    print("\nTroubleshooting steps:")
    print("1. Make sure Ollama is running: ollama serve")
    print("2. Verify the model is loaded: ollama list")
    print("3. Try restarting Ollama")
    sys.exit(1)
