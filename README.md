# Projet_agricole
# Tableau de Bord Agricole

Ce projet propose un tableau de bord interactif pour la visualisation des données agricoles, en utilisant les bibliothèques **Bokeh** et **Folium**. Le tableau de bord permet d'analyser l'évolution des rendements, les tendances NDVI, et de visualiser les données cartographiques des parcelles.

## Fonctionnalités

### 1. **Visualisation des Rendements**
- Graphique interactif présentant l'historique des rendements agricoles (`rendement_estime`) par parcelle.
- Affichage des tendances de rendement pour mieux comprendre les variations au fil du temps.

### 2. **Évolution du NDVI**
- Graphique montrant l'évolution du NDVI (indice de végétation) pour une parcelle donnée.
- Intégration de seuils historiques pour une meilleure évaluation des performances.


### 4. **Matrice de Stress**
- Analyse des relations entre les niveaux de stress hydrique et la température.

---

## Installation

### 1. **Prérequis**
Assurez-vous que les outils suivants sont installés sur votre système :
- **Python 3.8+**
- Bibliothèques Python nécessaires (listées ci-dessous)

### 2. **Clonez le Répertoire**
```bash
git clone <URL_DU_REPO>
cd projet_agricole
---

### Lancement du tableau de bord
python src/dashboard.py

