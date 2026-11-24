# Elecciones HN 2025

An independent count of the 2025 Honduras presidential election. A local vision model read the official actas (the tally sheet from each polling table), and the results are published department by department next to the CNE's own figures, so anyone can compare the two.

**Live site:** [milandroid.dev/eleccioneshn2025](https://milandroid.dev/eleccioneshn2025/). The site stopped updating on 19 December 2025.

> **En español:** un conteo independiente de la elección presidencial de Honduras 2025. Un modelo de visión local leyó las actas oficiales, y los resultados se publican por departamento junto a las cifras del CNE para que cualquiera pueda compararlas. El sitio dejó de actualizarse el 19 de diciembre de 2025.

## What it claims, and what it does not

The count adds up the votes exactly as they appear on the actas and uses only what those documents contain. It cannot tell whether an acta was altered: if an acta was manipulated, this count reflects the same manipulation. The project works from public information and is not affiliated with the CNE or any political party.

Because the source can't be verified, the project's job is to transcribe faithfully and show its work. Every number on the site traces back to the acta it came from.

## How the count was produced

1. **Download** every acta PDF published on the CNE portal: 19,137 in total.
2. **Convert** each PDF to an image with `pdf2image` and poppler.
3. **Read** the vote counts with a local vision model (`ministral-3` through Ollama) into one JSON file per acta. A local model was a deliberate choice: sending 19,137 documents through a hosted API would have been slow, expensive and dependent on someone else's service.
4. **Validate** each acta against its own arithmetic. Every acta lands in one of five buckets:
   - **Valid:** the party totals add up to the acta's *gran total*. Counted.
   - **Empty gran total:** the model read no overall total, so nothing can be checked.
   - **Gran total above 400:** a polling table can't hold more than 400 voters, so this is a misread digit.
   - **Sum ≠ gran total:** the parties add up to something other than the stated total, the clearest sign of a misread digit.
   - **Other errors:** anything else, kept separate instead of lumped together.
5. **Correct** the actas that fail. A small editor shows the original PDF next to the extracted values, a person fixes the digit, and the acta goes through validation again. Corrections are stored apart from the raw model output, so what the model originally read is never lost.

The pipeline and the correction tool are not in this repository. The [project page](https://milandroid.dev/projects/elecciones-hn-2025.html) describes them in more detail.

## What's in this repository

This repository holds the published site and the data behind it.

| Path | Contents |
|---|---|
| `index.html` | *Mi Conteo*: the independent count, by department |
| `conteo_cne.html` | The CNE's official results |
| `comparacion.html` | Comparison between the two counts |
| `actas.html` | Index of the actas, each traceable to its polling table |
| `proyeccion-simple.html`, `proyecciones-profundas.html` | Projections |
| `reports/actas_data/`, `reports/actas_data_transformed/` | The extracted data, one JSON file per acta, with each value in figures and in words |
| `reports/actas_data_cne/` | The CNE's published figures per acta, kept separate from the extracted ones |
| `reports/*.csv`, `reports/*.json` | Validation, inconsistency and coverage reports, plus the CNE's reference data on zonas, municipios and centros |

The pages load their data from the live site, not from the files next to them, so editing a file here doesn't change what a local copy shows.

## License

MIT. See [LICENSE](LICENSE). The license covers the site and the extracted data. It does not cover the CNE's own material, which is included for reference: its published figures in `reports/actas_data_cne/` and its data on zonas, municipios and centros.
