import logging
from bokeh.layouts import column, row
import numpy as np
import pandas as pd

from bokeh.models import (
    ColumnDataSource, Select, CustomJS, Span, HoverTool, 
    ColorBar, LinearColorMapper, BasicTicker
)
from bokeh.plotting import figure, show
from data_manager import AgriculturalDataManager
from bokeh.palettes import RdYlBu11 as palette

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

class AgriculturalDashboard:
    def __init__(self, data_manager):
        """
        Initialisation du tableau de bord avec le gestionnaire de données.
        """
        self.data_manager = data_manager
        self.full_yield_source = None
        self.full_ndvi_source = None
        self.yield_source = None
        self.ndvi_source = None
        self.stress_source = None
        self.full_stress_source = None
        self.features = None
        self.create_data_sources()

    def create_data_sources(self):
        """
        Charge les données, prépare les sources de données pour Bokeh.
        """
        try:
            self.data_manager.load_data()
            self.features = self.data_manager.prepare_features()

            # Vérifiez les colonnes nécessaires
            required_columns = {'parcelle_id', 'date', 'rendement_estime', 'ndvi'}
            missing_columns = required_columns - set(self.features.columns)
            if missing_columns:
                raise ValueError(f"Colonnes manquantes : {missing_columns}")

            # Vérifiez si les données sont vides
            yield_data = self.features[['parcelle_id', 'date', 'rendement_estime']].dropna()
            ndvi_data = self.features[['parcelle_id', 'date', 'ndvi']].dropna()

            if yield_data.empty:
                logging.warning("Les données de rendement sont vides.")
                self.yield_source = None
            else:
                self.yield_source = ColumnDataSource(yield_data)

            if ndvi_data.empty:
                logging.warning("Les données NDVI sont vides.")
                self.ndvi_source = None
            else:
                self.ndvi_source = ColumnDataSource(ndvi_data)

            logging.info("Sources de données préparées avec succès.")

        except Exception as e:
            logging.error(f"Erreur lors de la préparation des sources de données : {e}")
            self.yield_source = None
            self.ndvi_source = None


    def create_yield_history_plot(self, select_widget):
        """
        Crée et retourne un graphique de l'historique des rendements pour la parcelle sélectionnée.
        """
        try:
            plot_yield = figure(
                title="Historique des Rendements par Parcelle",
                x_axis_type="datetime",
                height=400,
                sizing_mode="stretch_both",
                tools="pan,wheel_zoom,box_zoom,reset,save",
                x_axis_label="Date",
                y_axis_label="Rendement (t/ha)"
            )
            plot_yield.line(
                x='date', y='rendement_estime',
                source=self.yield_source,
                line_width=2, color="purple", legend_label="Rendement"
            )
            plot_yield.circle(
                x='date', y='rendement_estime',
                source=self.yield_source, size=8, color="red", legend_label="Points"
            )

            plot_yield.add_tools(HoverTool(
                tooltips=[("Date", "@date{%F}"), ("Rendement", "@rendement_estime{0.2f} t/ha")],
                formatters={"@date": "datetime"}, mode="vline"
            ))

            plot_yield.legend.location = "top_left"
            plot_yield.legend.click_policy = "hide"

            callback_yield = CustomJS(
                args={
                    "source": self.yield_source,
                    "full_source": self.full_yield_source,
                    "select": select_widget
                },
                code="""
                    const full = full_source.data;
                    const filt = source.data;
                    const choix = select.value;

                    for (let k in filt) { filt[k] = []; }

                    let indices = [];
                    for (let i = 0; i < full['parcelle_id'].length; i++) {
                        if (full['parcelle_id'][i] === choix) { indices.push(i); }
                    }

                    indices.sort((a,b) => new Date(full['date'][a]) - new Date(full['date'][b]));

                    for (let key in filt) {
                        for (let i of indices) {
                            filt[key].push(full[key][i]);
                        }
                    }
                    source.change.emit();
                """
            )
            select_widget.js_on_change("value", callback_yield)
            return plot_yield
        except Exception as err:
            logging.error(f"Erreur lors de la création du graphique de rendement : {err}")
            return None

    def create_ndvi_temporal_plot(self, select_widget):
        """
        Crée et retourne un graphique de l'évolution du NDVI pour la parcelle sélectionnée.
        """
        try:
            plot_ndvi = figure(
                title="Évolution du NDVI avec Seuils Historiques",
                x_axis_type="datetime",
                height=400,
                sizing_mode="stretch_both",
                tools="pan,wheel_zoom,box_zoom,reset,save",
                x_axis_label="Date",
                y_axis_label="NDVI"
            )
            plot_ndvi.line(
                x='date', y='ndvi',
                source=self.ndvi_source,
                line_width=2, color="purple", legend_label="NDVI"
            )
            plot_ndvi.add_tools(HoverTool(
                tooltips=[("Parcelle", "@parcelle_id"), ("Date", "@date{%F}"), ("NDVI", "@ndvi{0.2f}")],
                formatters={"@date": "datetime"}, mode="vline"
            ))
            plot_ndvi.legend.location = "top_left"
            plot_ndvi.legend.click_policy = "hide"

            seuil = Span(location=0.5, dimension='width', line_color='blue', line_dash='dashed', line_width=2)
            plot_ndvi.add_layout(seuil)

            callback_ndvi = CustomJS(
                args={
                    "source": self.ndvi_source,
                    "full_source": self.full_ndvi_source,
                    "select": select_widget
                },
                code="""
                    const full = full_source.data;
                    const filt = source.data;
                    const choix = select.value;

                    for (let k in filt) { filt[k] = []; }
                    for (let i = 0; i < full['parcelle_id'].length; i++) {
                        if (full['parcelle_id'][i] === choix) {
                            for (let key in filt) {
                                filt[key].push(full[key][i]);
                            }
                        }
                    }
                    source.change.emit();
                """
            )
            select_widget.js_on_change("value", callback_ndvi)
            return plot_ndvi
        except Exception as err:
            logging.error(f"Erreur lors de la création du graphique NDVI : {err}")
            return None

    def create_stress_matrix(self, select_widget):
        """
        Crée et retourne une matrice de stress pour la parcelle sélectionnée.
        """
        try:
            if 'temperature' not in self.features.columns or 'stress_hydrique' not in self.features.columns:
                logging.warning("Colonnes 'temperature' et 'stress_hydrique' manquantes.")
                return None

            self.features['temp_bin'] = (self.features['temperature'] // 5) * 5
            self.features['stress_bin'] = (self.features['stress_hydrique'] // 0.1) * 0.1

            matrix = (self.features.groupby(['parcelle_id', 'temp_bin', 'stress_bin'])
                                    .size()
                                    .reset_index(name='count'))
            matrix['norm_count'] = matrix['count'] / matrix['count'].max()

            self.stress_source = ColumnDataSource(matrix)
            self.full_stress_source = ColumnDataSource(matrix)

            stress_plot = figure(
                title="Matrice de Stress",
                x_axis_label="Température (°C)",
                y_axis_label="Stress Hydrique (Index)",
                height=400,
                sizing_mode="stretch_both",
                tools="pan,wheel_zoom,box_zoom,reset,save",
            )
            mapper = LinearColorMapper(palette=palette, low=0, high=1)
            stress_plot.rect(
                x="temp_bin", y="stress_bin", width=1, height=1,
                source=self.stress_source,
                fill_color={"field": "norm_count", "transform": mapper},
                line_color=None,
            )

            color_bar = ColorBar(
                color_mapper=mapper,
                ticker=BasicTicker(),
                label_standoff=8,
                border_line_color=None,
                location=(0, 0),
                title="Densité Normalisée",
            )
            stress_plot.add_layout(color_bar, "right")

            stress_plot.add_tools(HoverTool(
                tooltips=[
                    ("Température", "@temp_bin°C"),
                    ("Stress Hydrique", "@stress_bin"),
                    ("Densité", "@norm_count{0.0%}")
                ]
            ))

            callback_stress = CustomJS(
                args={
                    "source": self.stress_source,
                    "full_source": self.full_stress_source,
                    "select": select_widget
                },
                code="""
                    const data = full_source.data;
                    const filt = source.data;
                    const choix = select.value;

                    filt["temp_bin"] = [];
                    filt["stress_bin"] = [];
                    filt["norm_count"] = [];

                    for (let i = 0; i < data["parcelle_id"].length; i++) {
                        if (data["parcelle_id"][i] === choix) {
                            filt["temp_bin"].push(data["temp_bin"][i]);
                            filt["stress_bin"].push(data["stress_bin"][i]);
                            filt["norm_count"].push(data["norm_count"][i]);
                        }
                    }
                    source.change.emit();
                """
            )
            select_widget.js_on_change("value", callback_stress)

            return stress_plot
        except Exception as err:
            logging.error(f"Erreur lors de la création de la matrice de stress : {err}")
            return None

    def create_yield_prediction_plot(self, select_widget):
        """
        Crée un graphique de prédiction des rendements pour la parcelle sélectionnée.
        """
        try:
            pred_plot = figure(
                title="Prédiction des Rendements",
                x_axis_type="datetime",
                height=400,
                sizing_mode="stretch_both",
                tools="pan,wheel_zoom,box_zoom,reset,save",
                x_axis_label="Date",
                y_axis_label="Rendement (t/ha)"
            )

            prediction_source = ColumnDataSource(data={
                "date": [], "actual_yield": [], "predicted_yield": []
            })

            pred_plot.line(
                x="date", y="actual_yield",
                source=prediction_source,
                line_width=2, color="blue", legend_label="Rendement Actuel"
            )
            pred_plot.line(
                x="date", y="predicted_yield",
                source=prediction_source,
                line_width=2, color="orange", legend_label="Rendement Prévu"
            )

            pred_plot.add_tools(HoverTool(
                tooltips=[
                    ("Date", "@date{%F}"),
                    ("Rendement Actuel", "@actual_yield{0.2f} t/ha"),
                    ("Rendement Prévu", "@predicted_yield{0.2f} t/ha")
                ],
                formatters={"@date": "datetime"}, mode="vline"
            ))
            pred_plot.legend.location = "top_left"
            pred_plot.legend.click_policy = "hide"

            callback_pred = CustomJS(
                args={
                    "source": prediction_source,
                    "full_source": self.full_yield_source,
                    "select": select_widget
                },
                code="""
                    const full = full_source.data;
                    const filt = source.data;
                    const choix = select.value;

                    filt["date"] = [];
                    filt["actual_yield"] = [];
                    filt["predicted_yield"] = [];

                    for (let i = 0; i < full['parcelle_id'].length; i++) {
                        if (full['parcelle_id'][i] === choix) {
                            filt["date"].push(full["date"][i]);
                            filt["actual_yield"].push(full["rendement_estime"][i]);
                            const pred = full["rendement_estime"][i] * (1 + 0.05 * (Math.random() - 0.5));
                            filt["predicted_yield"].push(pred);
                        }
                    }
                    source.change.emit();
                """
            )
            select_widget.js_on_change("value", callback_pred)

            return pred_plot
        except Exception as err:
            logging.error(f"Erreur lors de la création du graphique de prédiction : {err}")
            return None

    def get_parcelle_options(self):
        """
        Récupère et retourne les options de parcelles disponibles.
        """
        try:
            if self.data_manager.monitoring_data is None:
                raise ValueError("Données de monitoring non chargées.")
            return sorted(self.data_manager.monitoring_data["parcelle_id"].unique())
        except Exception as err:
            logging.error(f"Erreur lors de la récupération des options de parcelle : {err}")
            return []

    def create_layout(self):
        """
        Crée une mise en page simple pour le tableau de bord.
        """
        try:
            # Obtenir les options de parcelles
            parcels = self.get_parcelle_options()
            if not parcels:
                logging.warning("Aucune parcelle disponible.")
                return None

            # Widget de sélection de parcelle
            select_widget = Select(
                title="Sélectionnez une parcelle :",
                value=str(parcels[0]),
                options=list(map(str, parcels)),
                sizing_mode="stretch_width"
            )

            # Création des graphiques
            yield_hist_plot = self.create_yield_history_plot(select_widget)
            ndvi_temp_plot = self.create_ndvi_temporal_plot(select_widget)

            # Ajouter uniquement les graphiques qui sont valides
            plots = []
            if yield_hist_plot:
                plots.append(yield_hist_plot)
            if ndvi_temp_plot:
                plots.append(ndvi_temp_plot)

            if not plots:
                logging.error("Aucun graphique valide n'a été créé.")
                return None

            # Organisation simple : un widget de sélection et les graphiques en colonne
            layout = column(select_widget, *plots, sizing_mode="stretch_both")
            return layout

        except Exception as e:
            logging.error(f"Erreur lors de la création de la mise en page : {e}")
            return None




if __name__ == "__main__":
        mgr = AgriculturalDataManager()
        mgr.load_data()
        dashboard = AgriculturalDashboard(mgr)
        layout = dashboard.create_layout()
        if layout:
            show(layout)
        else:
            logging.error("La mise en page n'a pas pu être créée.")