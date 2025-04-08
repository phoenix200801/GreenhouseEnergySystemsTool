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
        Output(ids.COSTS_PIE_CHART, "children"),
        [
            Input(ids.ENERGY_DROPDOWN, "value"),
        ],
    )
    def update_pie_chart(selected_sources: list[str]) -> html.Div:
        if not selected_sources or len(selected_sources) == 0:
            return html.Div("Please select energy sources to display.", id=ids.COSTS_PIE_CHART)

        # Process cost data for selected sources
        cost_data = []
        for source in selected_sources:
            if source in OPTIMIZATION_DATA["optimised_cost_components"]:
                # Directly use the total field instead of calculating sum
                total_cost = OPTIMIZATION_DATA["optimised_cost_components"][source]["total"]
                if total_cost > 0:  # Only include sources with non-zero costs
                    cost_data.append({
                        'source': source,
                        'cost': total_cost
                    })

        if not cost_data:
            return html.Div("No significant cost data available for selected sources.", id=ids.COSTS_PIE_CHART)

        # Create DataFrame for plotting
        df = pd.DataFrame(cost_data)

        # Calculate total for percentage reference
        total_displayed_cost = df['cost'].sum()

        # Create the pie chart
        fig = px.pie(
            df,
            values='cost',
            names='source',
            title='Energy Source Cost Distribution',
            color='source',
            hover_data=['cost']
        )

        # Customize text to show both percentage and absolute values
        fig.update_traces(
            texttemplate='%{label}<br>%{percent}<br>€%{value:,.0f}',
            textposition='inside',
            hovertemplate='<b>%{label}</b><br>Cost: €%{value:,.0f}<br>Percentage: %{percent}'
        )

        # Improve layout
        fig.update_layout(
            legend_title=None,
            uniformtext_minsize=10,
            uniformtext_mode='hide'
        )

        return html.Div(dcc.Graph(figure=fig), id=ids.COSTS_PIE_CHART)

    return html.Div(id=ids.COSTS_PIE_CHART)