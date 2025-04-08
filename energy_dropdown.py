from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import json
from . import ids


# Load the optimization results data
def load_optimization_data():
    json_path = r"C:\Users\phoen\OneDrive - National University of Ireland, Galway\Masters\Thesis\Python Framework\Lib\optimization_results.json"
    with open(json_path, "r") as f:
        return json.load(f)


def render(app: Dash) -> html.Div:
    # Get available energy sources from the JSON file
    optimization_data = load_optimization_data()
    available_sources = list(optimization_data["capacities"].keys())

    @app.callback(
        Output(ids.ENERGY_DROPDOWN_CONTAINER, "children"),
        Input(ids.PAGE_LOCATION, "pathname"),
    )
    def render_energy_dropdown(_: str) -> html.Div:
        return html.Div(
            [
                html.H6("Energy Sources"),
                dcc.Dropdown(
                    id=ids.ENERGY_DROPDOWN,
                    options=[{"label": source, "value": source} for source in available_sources],
                    value=[source for source in available_sources
                           if str(optimization_data["capacities"].get(source, "NaN")).lower() != "nan"],
                    multi=True,
                ),
            ],
        )

    return html.Div(id=ids.ENERGY_DROPDOWN_CONTAINER)