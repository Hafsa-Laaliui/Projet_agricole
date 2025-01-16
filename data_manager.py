import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
import warnings
import logging


warnings.filterwarnings('ignore')

class AgriculturalDataManager:
    def __init__(self):
        """Initialise le gestionnaire de données agricoles"""
        self.monitoring_data = None
        self.weather_data = None
        self.soil_data = None
        self.yield_history = None
        self.scaler = StandardScaler()

    def load_data(self):
        """
        Charge l’ensemble des données nécessaires au système
        Effectue les conversions de types et les indexations temporelles
        """
        self.monitoring_data = pd.read_csv('C:/Users/Zeen/projet_agricole2/data/monitoring_cultures.csv', parse_dates=['date'])
        self.weather_data = pd.read_csv('C:/Users/Zeen/projet_agricole2/data/meteo_detaillee.csv', parse_dates=['date'])
        self.soil_data = pd.read_csv('C:/Users/Zeen/projet_agricole2/data/sols.csv')
        self.yield_history = pd.read_csv('C:/Users/Zeen/projet_agricole2/data/historique_rendements.csv', parse_dates=['date'])

    def _setup_temporal_indices(self):
        """
        Configure les index temporels pour les différentes séries
        de données et vérifie leur cohérence
        """
        self.monitoring_data.set_index('date', inplace=True)
        self.weather_data.set_index('date', inplace=True)
        self.yield_history.set_index('date', inplace=True)

    def _verify_temporal_consistency(self):
        """
        Vérifie la cohérence des périodes temporelles entre
        les différents jeux de données
        """
        if not self.monitoring_data.index.is_monotonic:
            raise ValueError("Les données de monitoring ne sont pas triées par date.")
        if not self.weather_data.index.is_monotonic:
            raise ValueError("Les données météorologiques ne sont pas triées par date.")
        if not self.yield_history.index.is_monotonic:
            raise ValueError("Les données historiques de rendements ne sont pas triées par date.")

    def prepare_features(self):
        """
        Prépare les caractéristiques pour l’analyse en fusionnant
        les différentes sources de données.
        """
        try:
            # Vérification et conversion des dates
            self.monitoring_data['date'] = pd.to_datetime(self.monitoring_data['date'])
            self.weather_data['date'] = pd.to_datetime(self.weather_data['date'])
            self.yield_history['date'] = pd.to_datetime(self.yield_history['date'])

            self.monitoring_data.set_index('date', inplace=True)
            self.weather_data.set_index('date', inplace=True)

            # Agrégation des données
            numeric_cols_monitoring = self.monitoring_data.select_dtypes(include=[np.number]).columns
            monitoring_monthly = self.monitoring_data[numeric_cols_monitoring.tolist() + ['parcelle_id']].groupby(
                [pd.Grouper(freq='M'), 'parcelle_id']
            ).mean().reset_index()

            numeric_cols_weather = self.weather_data.select_dtypes(include=[np.number]).columns
            weather_monthly = self.weather_data[numeric_cols_weather].groupby(
                pd.Grouper(freq='M')
            ).mean().reset_index()

            # Fusions successives
            combined_data = pd.merge_asof(
                monitoring_monthly.sort_values('date'),
                weather_monthly.sort_values('date'),
                on='date'
            )
            combined_data = pd.merge(
                combined_data,
                self.soil_data,
                how='left',
                on='parcelle_id'
            )

            # Fusion avec yield_history
            if 'rendement_estime' in self.yield_history.columns:
                combined_data = pd.merge_asof(
                    combined_data.sort_values('date'),
                    self.yield_history[['date', 'parcelle_id', 'rendement_estime']].sort_values('date'),
                    on='date',
                    by='parcelle_id'
                )
            else:
                raise KeyError("'rendement_estime' n'est pas présent dans yield_history")

            # Vérifiez si les colonnes nécessaires existent
            if 'rendement_estime' not in combined_data.columns:
                raise KeyError("'rendement_estime' n'est pas présent après la fusion.")

            combined_data.dropna(inplace=True)

            # Mise à l'échelle des données numériques
            numeric_cols = combined_data.select_dtypes(include=[np.number]).columns
            combined_data[numeric_cols] = self.scaler.fit_transform(combined_data[numeric_cols])

            logging.info(f"Colonnes disponibles après fusion : {combined_data.columns}")
            return combined_data

        except Exception as e:
            logging.error(f"Erreur lors de la préparation des caractéristiques : {e}")
            raise




    def _enrich_with_yield_history(self, data):
        """
        Enrichit les données actuelles avec les informations
        historiques des rendements
        """
        enriched_data = pd.merge(
            data,
            self.yield_history,
            how='left',
            on=['date', 'parcelle_id']
        )
        return enriched_data

    def get_temporal_patterns(self, parcelle_id):
        """
        Analyse les patterns temporels pour une parcelle donnée
        """
        parcelle_data = self.monitoring_data[self.monitoring_data['parcelle_id'] == parcelle_id]
        
        # Fusionner avec yield_history pour inclure 'rendement_estime'
        if 'rendement_estime' in self.yield_history.columns:
            parcelle_data = pd.merge(
                parcelle_data.reset_index(),  # Reset index to allow merging on 'date'
                self.yield_history[['date', 'parcelle_id', 'rendement_estime']],
                how='left',
                on=['date', 'parcelle_id']
            )
        else:
            raise KeyError("'rendement_estime' est absent des données yield_history.")
        # Analyse temporelle à implémenter selon le besoin
        return parcelle_data

    def calculate_risk_metrics(self, data):
        """
        Calcule les métriques de risque basées sur les conditions
        actuelles et l’historique
        """
        # Exemple de calcul d’un score de risque fictif
        data['risk_score'] = data['stress_hydrique'] * 0.5 + data['biomasse_estimee'] * 0.3
        return data[['parcelle_id', 'date', 'risk_score']]
    def analyze_yield_patterns(self, parcelle_id):
            """
            Réalise une analyse approfondie des patterns de rendement
            """
            from statsmodels.tsa.seasonal import seasonal_decompose

            # Extraction et préparation des données
            history = self.yield_history[
                self.yield_history['parcelle_id'] == parcelle_id
            ].copy()

            # Décomposition saisonnière des rendements estimés
            if 'rendement_estime' in history.columns:
                decomposition = seasonal_decompose(history.set_index('date')['rendement_estime'], model='additive', period=12)
                result = {
                    'trend': decomposition.trend,
                    'seasonal': decomposition.seasonal,
                    'residual': decomposition.resid
                }
                return result
            else:
                raise KeyError("'rendement_estime' est absent des données pour l'analyse des patterns.")


# Initialisation du gestionnaire de données
data_manager = AgriculturalDataManager()

# Chargement des données
data_manager.load_data()

# Préparation des caractéristiques
features = data_manager.prepare_features()

# Analyse des patterns temporels pour une parcelle spécifique
parcelle_id = 'P001'
try:
    # Analyze yield patterns
    analysis_results = data_manager.analyze_yield_patterns(parcelle_id)

    # Print results
    print("Trend component:")
    print(analysis_results['trend'].dropna())  # Drop NaN values for clarity
    print("\nSeasonal component:")
    print(analysis_results['seasonal'].dropna())  # Drop NaN values for clarity
    print("\nResidual component:")
    print(analysis_results['residual'].dropna())  # Drop NaN values for clarity

except KeyError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
    
history = data_manager.get_temporal_patterns(parcelle_id)

# Vérifiez les colonnes de history avant d'accéder à 'rendement_estime'
print("Colonnes disponibles dans history :", history.columns)

# Assurez-vous que la colonne est accessible avant d'utiliser .mean()
if 'rendement_estime' in history.columns:
    print(f"Tendance de rendement : {history['rendement_estime'].mean():.2f} tonnes/ha/an")
else:
    raise KeyError("La colonne 'rendement_estime' est absente dans le DataFrame history.")



