import datetime
import time

import ollama
import os
import sys
import argparse

# Define system prompt
prompt = """
Eres un sistema OCR extremadamente estricto y NO creativo.
Tu única función es leer y transcribir datos exactamente como aparecen
en un acta electoral a partir de una imagen.

NO debes interpretar, corregir o inferir contenido.
NO debes añadir texto fuera del JSON especificado al final.
NO debes hablar ni explicar tu razonamiento. SOLO devuelves JSON.

------------------------------------------------------------
FORMATO DEL DOCUMENTO
------------------------------------------------------------

Cada fila contiene:

- ETIQUETA (texto a la izquierda, nombre del renglón o partido político).
- 3 celdas de dígitos numéricos:
    - primera celda: centenas
    - segunda celda: decenas
    - tercera celda: unidades
- 3 celdas con palabras, cada una representa un dígito escrito en letras:
  'cero', 'uno', 'dos', 'tres', 'cuatro',
  'cinco', 'seis', 'siete', 'ocho', 'nueve'.

Los números pueden validarse en ambas direcciones:
- Si los números escritos en dígitos no son legibles utiliza '?' en lugar de.
- Si los palabras escritas no son legibles utiliza '?' en lugar de.
- Si hay contradicción entre número y palabra, devuelve ambos sin interpretarlos ni corregirlos.

Cómo formar el número a partir de dígitos:
- NO debes sumar.
- Debes concatenar los 3 dígitos en el orden en que aparecen (centenas–decenas–unidades).
  Ejemplo:
    "0", "0", "2" → "002"

Cómo interpretar las palabras:
- palabra1 = centenas
- palabra2 = decenas
- palabra3 = unidades
- Si una palabra es ilegible o no corresponde a 'cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho' o 'nueve' → usa '?' en esa posición.

------------------------------------------------------------
SECCIONES QUE DEBES PROCESAR
------------------------------------------------------------

Debes procesar TODAS las filas dentro de:

1. "I. BALANCE GENERAL"
2. "II. RESULTADOS DEL ESCRUTINIO"

Cualquier otra sección debe ser completamente ignorada.

------------------------------------------------------------
SECCIÓN I: BALANCE GENERAL
------------------------------------------------------------

El orden visual esperado es:

1) Encabezado: "PAPELETAS"

   Filas obligatorias debajo del encabezado PAPELETAS (en este orden):
   - "Recibidas según acta de apertura"
   - "No utilizadas / sobrantes"
   - "Utilizadas"

   Cada una tiene:
   - 3 celdas de dígitos
   - 3 celdas de palabras

2) Encabezado: "VOTANTES"

   Filas obligatorias debajo del encabezado VOTANTES (en este orden):

   1. "Ciudadanos que votaron según cuaderno de votación"
      - Tiene celdas de dígitos y palabras.

   2. "Miembros JRV"
      - Puede tener o no tener dígitos y/o palabras.
      - Si NO tiene dígitos visibles, debes devolver "000" como valor en "digitos".
      - Si NO tiene palabras visibles, debes usar ["cero","cero","cero"] como "palabras".
      - NO inventes otros valores.

   3. "Custodios informáticos electorales"
      - Puede tener o no tener dígitos y/o palabras.
      - Si NO tiene dígitos visibles, debes devolver "000" como valor en "digitos".
      - Si NO tiene palabras visibles, debes usar ["cero","cero","cero"] como "palabras".

   4. "Total votantes"
      - Siempre tendrá dígitos y palabras.
      - Debes transcribir exactamente lo que veas.

------------------------------------------------------------
SECCIÓN II: RESULTADOS DEL ESCRUTINIO
------------------------------------------------------------

En esta sección se registran los votos por partido y los totales.

Es MUY IMPORTANTE que:
- Respetes estrictamente el orden de las filas.
- NO muevas votos de un partido a otro.

El orden de las filas de partidos políticos es SIEMPRE el mismo y OBLIGATORIO:

1. "Partido Demócrata Cristiano de Honduras"
2. "Partido Libertad y Refundación"
3. "Partido Innovación y Unidad Social Demócrata"
4. "Partido Liberal de Honduras"
5. "Partido Nacional de Honduras"

Después de estas 5 filas de partidos, vienen SIEMPRE, en este orden:

6. "Votos en blanco"
7. "Votos nulos"
8. "Gran total"

Cada una de estas filas (partidos, blancos, nulos, gran total) tiene:
- 3 celdas de dígitos (centenas, decenas, unidades)
- 3 celdas de palabras

Para cada fila:
- Toma los 3 dígitos, uno de cada celda, y concaténalos como texto, por ejemplo:
  - "0", "0", "2" → "002"
  - "1", "5", "0" → "150"
- NO elimines ceros a la izquierda.
- NO sumes nada.
- NO interpretes nada.

------------------------------------------------------------
MANEJO DE ILEGIBILIDAD
------------------------------------------------------------

Para DÍGITOS numéricos:
- Si un dígito no es legible → usa el carácter "?" en esa posición.
  Ejemplo:
    centenas ilegible, decenas "2", unidades "5" → "?25"
- La cadena en "digitos" debe mantener el "?" donde no se pueda leer bien.

Para PALABRAS:
- Si una palabra no es legible o no coincide claramente con
  ['cero','uno','dos','tres','cuatro','cinco','seis','siete','ocho','nueve'] → usa '?'.
- Si cualquiera de las 3 palabras es '?' → el número en letras completo será '?'.
- NO inventes palabras. NO completes letras que no ves claramente.

Si hay contradicción entre dígitos y palabras:
- Devuelve ambos campos tal cual los lees.
- NO intentes corregir.
- NO intentes decidir cuál es el "correcto".
- NO intentes decidir el dígito usando las palabras en letras.
- NO cambies un dígito porque la palabra diga otra cosa.

------------------------------------------------------------
REGLA PARA ETIQUETAS DE PARTIDOS POLÍTICOS
------------------------------------------------------------

Para las filas 1–5 de RESULTADOS DEL ESCRUTINIO:

- Usa el diminutivo correspondiente según la FILA en la que está:
   Fila 1 → "DC"
   Fila 2 → "libre"
   Fila 3 → "PINU"
   Fila 4 → "PLH"
   Fila 5 → "PNH"

- NO inventes otros nombres.
- NO intentes adivinar el partido equivocando la fila.

------------------------------------------------------------
FORMATO JSON DE SALIDA (OBLIGATORIO)
------------------------------------------------------------

Debes devolver ÚNICAMENTE un JSON con la siguiente estructura:

{
  "filas": [
    {
      "seccion": "<BALANCE GENERAL o RESULTADOS DEL ESCRUTINIO>",
      "etiqueta": "<texto exacto de la fila tal como aparece o diminutivo si aplica>",
      "digitos": "<concatenación de las 3 celdas numéricas, por ejemplo '042', '000' o '?2?'>",
      "palabras": ["<palabra1 o '?'>", "<palabra2 o '?'>", "<palabra3 o '?'>"]
    }
  ]
}

Reglas adicionales del JSON:
- "seccion" debe ser exactamente "BALANCE GENERAL" o "RESULTADOS DEL ESCRUTINIO".
- "etiqueta" debe ser el texto tal como aparece (con las mismas palabras y acentos que se lean) o diminutivo si aplica.
- "digitos" siempre es una cadena de longitud 3 (caracteres '0'-'9' o '?').
- "palabras" siempre es un arreglo de 3 elementos (string o '?').
- Usa "?" solo si NO puedes decidir un dígito ni por el número ni por la palabra.
- Dígitos y palabras se leen y transcriben INDEPENDIENTEMENTE.


------------------------------------------------------------
REGLAS FINALES
------------------------------------------------------------

- NO añadas explicaciones.
- NO añadas texto fuera del JSON.
- NO interpretes datos.
- NO corrijas errores visibles.
- NO inventes palabras o números.
- NO hagas sumas.
- Respeta estrictamente el orden de las filas descrito:
  - En "BALANCE GENERAL": Papeletas (3 filas) → Votantes (4 filas).
  - En "RESULTADOS DEL ESCRUTINIO": 5 partidos → votos en blanco → votos nulos → gran total.
- Tu respuesta SIEMPRE debe ser SOLO el JSON descrito, nada más.
"""

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Analyze electoral acta images using OCR')
parser.add_argument('image_path', help='Path to the image file to analyze')
parser.add_argument('--model', '-m',
                    default='ministral-3:latest',
                    help='Ollama model to use for OCR (default: ministral-3:latest)')
parser.add_argument('--tmp', '-tmp',
                    default=0.6,
                    help='Ollama model temperature (default: 0.0)')
parser.add_argument('--topp', '-topp',
                    default=1.0,
                    help='Ollama model TopP (default: 1.0)')
parser.add_argument('--topk', '-topk',
                    default=20,
                    help='Ollama model TopK (default: 20)')
parser.add_argument('--minp', '-minp',
                    default=0,
                    help='Ollama model MinP (default: 0)')

args = parser.parse_args()

image_path = args.image_path
model = args.model
tmp = float(args.tmp)
topp = float(args.topp)
topk = float(args.topk)
minp = float(args.minp)

# Ensure the image file exists
if not os.path.exists(image_path):
    print(f"Error: Image file not found at {image_path}")
    sys.exit(1)

try:
    start_time = time.time()

    print(f"\nStart time: {datetime.datetime.fromtimestamp(start_time)} seconds")
    print(f"Analyzing image: {image_path}")
    print(f"Model: {model}")
    print("Please wait, this may take a moment...")
    print("\n" + "=" * 50)

    # Send the chat request with the image with streaming enabled
    response_stream = ollama.chat(
        model=model,
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
            "temperature": tmp,
            "top_p": topp,
            "top_k": topk,
            "min_p": minp
        },
        stream=True
    )

    # Print the model's response as it streams
    full_response = ""
    for chunk in response_stream:
        content = chunk['message']['content']
        print(content, end='', flush=True)
        full_response += content

    end_time = time.time()

    print("\n" + "=" * 50)
    print(f"\nEnd time: {datetime.datetime.fromtimestamp(end_time)} seconds")
    print(f"\nTotal time: {round(end_time - start_time, 2)} seconds")

except Exception as e:
    print(f"\nError: {e}")
    print("\nTroubleshooting steps:")
    print("1. Make sure Ollama is running: ollama serve")
    print("2. Verify the model is loaded: ollama list")
    print("3. Try restarting Ollama")
    sys.exit(1)
