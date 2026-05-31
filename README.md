# MLPOS Credit Scoring

Projet universitaire de Machine Learning / MLOps pour predire le defaut de paiement d'un client bancaire.

## Objectif metier

Le modele predit si un client sera `Good` ou `Bad` a partir du pret courant, des donnees demographiques disponibles et de l'historique des prets precedents. La classe `Bad` est encodee en `1`, la classe `Good` en `0`.

## Structure

```text
data/raw/          CSV source
data/processed/    datasets finaux, resultats, soumission
notebooks/         notebooks explicatifs
src/               code reproductible
tests/             tests pytest
models/            modele sauvegarde
reports/figures/   figures d'evaluation
```

## Installation

```bash
pip install -r requirements.txt
```

## Commandes

```bash
python src/train.py
python src/predict.py
pytest tests/
mlflow ui --host 0.0.0.0 --port 5000
docker build -t mlpos-credit-scoring .
docker run --rm mlpos-credit-scoring
docker compose up --build
```

Avec Docker Compose, le service `mlflow-ui` est l'unique proprietaire de la
base SQLite MLflow. Le service d'entrainement attend que MLflow soit pret puis
envoie ses runs au tracking server HTTP. Les metadonnees et artefacts MLflow
sont persistants dans des volumes Docker nommes.

## Methodologie

- `trainperf.csv` et `testperf.csv` sont les tables maitres.
- Les jointures sont des `left join` sur `customerid`.
- Les demographics sont dedupliques par `customerid`.
- Les anciens prets sont agreges par `customerid`.
- `good_bad_flag`, `customerid` et `systemloanid` sont exclus des features.
- Les dates de `testperf` sont traitees avec prudence et ne sont pas utilisees comme variables principales.
- Les metriques analysent explicitement la classe `Bad`: precision, recall, F1, ROC AUC et PR AUC.

## Resultats

Apres entrainement, consulter :

- `data/processed/model_comparison.csv`
- `data/processed/*_thresholds.csv`
- `reports/figures/`
- MLflow UI

## Limites

Les donnees demographiques couvrent peu le test, certaines colonnes sont tres incompletes, les dates de `testperf` sont cassees et la validation n'est pas une vraie validation temporelle.
