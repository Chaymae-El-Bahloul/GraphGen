# ðŸ“Š GraphGen

[![CI](https://github.com/Chaymae-El-Bahloul/GraphGen/actions/workflows/ci.yml/badge.svg)](https://github.com/Chaymae-El-Bahloul/GraphGen/actions)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Application web qui transforme un fichier **CSV ou Excel** en **analyse exploratoire et graphiques interactifs**, sans Ã©crire de code.

**DÃ©mo en ligne:** _(ajouter le lien aprÃ¨s dÃ©ploiement)_

> _Capture d'Ã©cran: `docs/screenshot.png`_

## FonctionnalitÃ©s
**Import**
- Fichiers `.csv` et `.xlsx` (multi-feuilles, 10 Mo max), glisser-dÃ©poser
- DÃ©tection automatique du sÃ©parateur CSV, de l'encodage et de la **ligne d'en-tÃªte Excel**
- Bouton Â« dÃ©mo Â» avec un jeu de donnÃ©es intÃ©grÃ©

**Exploration**
- Indicateurs clÃ©s: lignes, colonnes, % de valeurs manquantes, doublons
- **Profil de chaque colonne**: type, manquants, valeurs uniques, min / max / moyenne
- **Matrice de corrÃ©lation** interactive

**Visualisation**
- 6 types de graphiques: ligne, barres, nuage de points, histogramme, boÃ®te Ã  moustaches, camembert
- AgrÃ©gations (somme, moyenne, nombre, min, max), regroupement par couleur
- 5 palettes, titre personnalisable, **export HTML interactif**
- Interface responsive avec mode sombre automatique

## QualitÃ© & sÃ©curitÃ©
- Fichiers stockÃ©s sous identifiant alÃ©atoire (pas de path traversal), extensions validÃ©es, taille limitÃ©e
- **Suppression automatique** des fichiers importÃ©s aprÃ¨s 24 h (`UPLOAD_TTL_HOURS`)
- En-tÃªtes de sÃ©curitÃ© HTTP, route `/health`, logs structurÃ©s
- 12 tests `pytest`, linter `ruff`, intÃ©gration continue GitHub Actions
- Conteneur Docker non-root avec healthcheck

## Installation
```bash
git clone https://github.com/Chaymae-El-Bahloul/GraphGen.git
cd GraphGen
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Ouvrir http://127.0.0.1:5000

### Docker
```bash
docker build -t graphgen .
docker run -p 8000:8000 -e SECRET_KEY=change-me graphgen
```

## DÃ©veloppement
```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

## Architecture
```
GraphGen/
â”œâ”€â”€ app.py             # Routes Flask, sÃ©curitÃ©, configuration
â”œâ”€â”€ helpers.py         # Chargement, profilage, corrÃ©lations, graphiques (sans Flask)
â”œâ”€â”€ templates/         # Jinja2: base, index, preview, chart
â”œâ”€â”€ static/style.css   # ThÃ¨me clair/sombre, responsive
â”œâ”€â”€ sample_data/       # Jeu de dÃ©monstration synthÃ©tique
â”œâ”€â”€ tests/             # pytest
â”œâ”€â”€ Dockerfile Â· Procfile Â· pyproject.toml
â””â”€â”€ .github/workflows/ci.yml
```

## Configuration
| Variable | RÃ´le | DÃ©faut |
|---|---|---|
| `SECRET_KEY` | ClÃ© de session Flask (**Ã  dÃ©finir en production**) | valeur de dev |
| `UPLOAD_TTL_HOURS` | DurÃ©e de conservation des fichiers | `24` |
| `FLASK_DEBUG` | `1` pour le mode debug local | dÃ©sactivÃ© |

## DÃ©ploiement
Render / Railway: build `pip install -r requirements.txt`, start `gunicorn "app:create_app()"` (voir `Procfile`), puis dÃ©finir `SECRET_KEY`.

## Pistes d'amÃ©lioration
Export PNG, filtres sur les donnÃ©es, graphiques multi-sÃ©ries, authentification.

## Licence
MIT


