import plotly.express as px
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import json
import pandas as pd
from . import ids


# Load the optimization results data
def load_optimization_data():
    json_path = r"C:\Users\phoen\OneDrive - National University of Ireland, Galway\Masters\Thesis\Python Framework\Lib\optimization_results.json"
    with open(json_path, "r") as f:
        return json.load(f)


# Replace the joblib loading with json loading
OPTIMIZATION_DATA = load_optimization_data()


def render(app: Dash) -> html.Div:
    @app.callback(
        Output(ids.CAPACITIES_BAR_CHART, "children"),
        [
            Input(ids.ENERGY_DROPDOWN, "value"),
        ],
    )
    def update_bar_chart(selected_sources: list[str]) -> html.Div:
        if not selected_sources or len(selected_sources) == 0:
            return html.Div("Please select energy sources to display.", id=ids.CAPACITIES_BAR_CHART)

        # Filter data for selected sources
        capacities = {source: OPTIMIZATION_DATA["capacities"].get(source, 0)
                      for source in selected_sources
                      if str(OPTIMIZATION_DATA["capacities"].get(source, "NaN")).lower() != "nan"}

        if not capacities:
            return html.Div("No data available for selected sources.", id=ids.CAPACITIES_BAR_CHART)

        # Create DataFrame for plotting
        df = pd.DataFrame({
            'source': list(capacities.keys()),
            'capacity': list(capacities.values())
        })

        # Create the bar chart
        fig = px.bar(
            df,
            x='source',
            y='capacity',
            title='Energy Source Capacities',
            labels={'capacity': 'Capacity (MW)', 'source': 'Energy Source'},
            color='source'
        )

        # Improve layout
        fig.update_layout(
            xaxis_tickangle=-45,
            legend_title=None
        )

        return html.Div(dcc.Graph(figure=fig), id=ids.CAPACITIES_BAR_CHART)

    return html.Div(id=ids.CAPACITIES_BAR_CHART)