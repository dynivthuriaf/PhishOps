# PhishOps

PhishOps est un projet MLOps de détection de sites de phishing à partir des caractéristiques techniques d'une URL et de sa page web. Il couvre le cycle de vie complet du modèle : ingestion depuis MongoDB, validation et détection de dérive, transformation, comparaison de plusieurs classifieurs, suivi d'expériences avec MLflow, sauvegarde des artefacts et exposition des prédictions via une API FastAPI.

## Fonctionnalités

- pipeline d'entraînement modulaire en Python ;
- validation du schéma et détection de dérive avec le test de Kolmogorov-Smirnov ;
- comparaison de modèles scikit-learn et sélection automatique du meilleur ;
- suivi local ou distant des expériences avec MLflow ;
- API FastAPI pour entraîner le modèle et prédire depuis un fichier CSV ;
- conteneurisation Docker ;
- déploiement continu vers Amazon ECR et une machine EC2 avec GitHub Actions.

## Pipeline

```text
MongoDB -> Ingestion -> Validation -> Transformation -> Entraînement -> MLflow
                                                           |
                                                           v
                                              Modèle + préprocesseur
                                                           |
                                                           v
                                                     API FastAPI
```

## Structure du projet

```text
PhishOps/
|-- .github/workflows/       # Pipeline CI/CD GitHub Actions
|-- data_schema/             # Schéma attendu par le pipeline
|-- final_model/             # Modèle et préprocesseur prêts à l'emploi
|-- Network_Data/            # Jeu de données de démonstration
|-- networksecurity/
|   |-- components/          # Ingestion, validation, transformation, entraînement
|   |-- pipeline/            # Orchestration du pipeline
|   |-- entity/              # Configurations et artefacts
|   |-- utils/               # Fonctions ML et utilitaires
|   `-- cloud/               # Synchronisation avec Amazon S3
|-- templates/               # Résultat HTML des prédictions
|-- app.py                   # API FastAPI
|-- main.py                  # Entraînement local
`-- Dockerfile
```

## Installation locale

### Prérequis

- Python 3.10 ;
- Git ;
- MongoDB local ou MongoDB Atlas pour réentraîner le modèle ;
- AWS CLI configuré uniquement pour la synchronisation S3 et le déploiement AWS.

### Windows PowerShell

```powershell
git clone https://github.com/dynivthuriaf/PhishOps.git
cd PhishOps
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

### Linux ou macOS

```bash
git clone https://github.com/dynivthuriaf/PhishOps.git
cd PhishOps
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Le modèle préentraîné est déjà présent dans `final_model/`. L'API de prédiction peut donc démarrer sans MongoDB ni AWS :

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Ouvrir ensuite la documentation interactive sur <http://localhost:8000/docs>.

## Utilisation de l'API

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/health` | Vérifie que l'API répond |
| `POST` | `/predict` | Accepte un fichier CSV et retourne les prédictions |
| `GET` | `/train` | Exécute le pipeline complet, y compris les synchronisations S3 |

Le fichier envoyé à `/predict` doit contenir les 30 variables décrites dans `data_schema/schema.yaml`, sans la colonne cible `Result`. La prédiction est ajoutée dans `predicted_column` et une copie est enregistrée dans `prediction_output/output.csv`.

Exemple :

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "accept: text/html" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@samples.csv;type=text/csv"
```

## Réentraînement

1. Renseigner `MONGO_DB_URL` dans `.env`.
2. Charger le jeu de données fourni dans MongoDB :

   ```bash
   python push_data.py
   ```

3. Lancer un entraînement local :

   ```bash
   python main.py
   ```

Le pipeline lit la collection `NetworkData` de la base `KRISHAI`. Les artefacts sont créés dans `Artifacts/` et le meilleur modèle est copié dans `final_model/`.

MLflow utilise par défaut un stockage local dans `mlruns/`. Pour envoyer les expériences vers un serveur distant tel que DagsHub, renseigner également `MLFLOW_TRACKING_URI`, `MLFLOW_TRACKING_USERNAME` et `MLFLOW_TRACKING_PASSWORD`.

La route `/train` ajoute à l'entraînement la synchronisation des artefacts et modèles vers Amazon S3. Elle nécessite une configuration AWS valide et l'accès au bucket défini par `TRAINING_BUCKET_NAME`.

## Exécution avec Docker

```bash
docker build -t phishops:latest .
docker run --rm --name phishops -p 8000:8000 --env-file .env phishops:latest
```

L'API est alors disponible sur <http://localhost:8000/docs>.

## Déploiement sur AWS

Le workflow `.github/workflows/main.yml` déploie automatiquement chaque push sur la branche `main` :

1. validation du dépôt ;
2. construction de l'image Docker ;
3. publication de l'image `latest` dans Amazon ECR ;
4. récupération et lancement de l'image sur un runner GitHub auto-hébergé, par exemple une instance EC2.

### Préparation AWS

1. Créer un dépôt privé Amazon ECR, par exemple `phishops`.
2. Créer une instance EC2, installer Docker et y enregistrer un runner GitHub Actions auto-hébergé pour ce dépôt.
3. Autoriser le port TCP `8000` dans le groupe de sécurité EC2, de préférence uniquement depuis les adresses qui doivent accéder à l'API.
4. Donner au compte ou rôle de déploiement les droits nécessaires sur ECR.
5. Ajouter les secrets suivants dans **GitHub > Settings > Secrets and variables > Actions** :

| Secret | Exemple ou rôle |
|---|---|
| `AWS_ACCESS_KEY_ID` | Identifiant du compte ou rôle AWS |
| `AWS_SECRET_ACCESS_KEY` | Clé secrète AWS |
| `AWS_REGION` | `eu-west-3` |
| `AWS_ECR_LOGIN_URI` | `123456789012.dkr.ecr.eu-west-3.amazonaws.com` |
| `ECR_REPOSITORY_NAME` | `phishops` |
| `TRAINING_BUCKET_NAME` | Bucket S3 utilisé par le pipeline, par exemple `phishops` |
| `MONGO_DB_URL` | Facultatif, requis pour `/train` |
| `MLFLOW_TRACKING_URI` | Facultatif |
| `MLFLOW_TRACKING_USERNAME` | Facultatif |
| `MLFLOW_TRACKING_PASSWORD` | Facultatif |

Après le premier déploiement, l'API est accessible sur `http://<IP_PUBLIQUE_EC2>:8000/docs`.

> La route `/train` déclenche un traitement coûteux et doit être protégée ou désactivée avant d'exposer l'API publiquement.

## Variables d'environnement

Ne jamais committer le fichier `.env`. Utiliser `.env.example` comme modèle et conserver les secrets dans un gestionnaire dédié ou dans GitHub Actions.

## Auteur

Projet maintenu par [dynivthuriaf](https://github.com/dynivthuriaf).
