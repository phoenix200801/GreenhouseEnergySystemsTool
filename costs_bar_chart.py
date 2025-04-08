import plotly.graph_objects as go
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import json
import pandas as pd
from . import ids


def load_optimization_data():
    json_path = r"C:\Users\phoen\OneDrive - National University of Ireland, Galway\Masters\Thesis\Python Framework\Lib\optimization_results.json"
    with open(json_path, "r") as f:
        return json.load(f)


OPTIMIZATION_DATA = load_optimization_data()


def render(app: Dash) -> html.Div:
    @app.callback(
        Output(ids.COSTS_BAR_CHART, "children"),
        [Input(ids.ENERGY_DROPDOWN, "value")],
    )
    def update_bar_chart(selected_sources: list[str]) -> html.Div:
        if not selected_sources or len(selected_sources) == 0:
            return html.Div("Please select energy sources to display.", id=ids.COSTS_BAR_CHART)

        # Process cost data for selected sources
        cost_data = []
        for source in selected_sources:
            if source in OPTIMIZATION_DATA["optimised_cost_components"]:
                total_cost = OPTIMIZATION_DATA["optimised_cost_components"][source]["total"]
                if total_cost > 0:  # Only include sources with non-zero costs
                    cost_data.append({
                        'source': source,
                        'cost': total_cost
                    })

        if not cost_data:
            return html.Div("No significant cost data available for selected sources.", id=ids.COSTS_BAR_CHART)

        # Create DataFrame for plotting
        df = pd.DataFrame(cost_data)

        # Create figure using Graph Objects
        fig = go.Figure()

        # Color palette for the bars
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22',
                  '#17becf']

        # Add bar trace
        fig.add_trace(
            go.Bar(
                x=df['source'],
                y=df['cost'],
                marker_color=[colors[i % len(colors)] for i in range(len(df))],  # Cycle through colors
                marker_line_color='rgba(0,0,0,0.3)',
                marker_line_width=1
            )
        )

        # Update layout
        fig.update_layout(
            title='Energy Source Total Costs',
            xaxis_title='Energy Source',
            yaxis_title='Total Cost (€)',
            xaxis_tickangle=-45,
            plot_bgcolor='white',
            showlegend=False,
            yaxis=dict(
                gridcolor='lightgray',
                tickprefix='€',
                tickformat=',.0f'
            ),
            margin=dict(t=50, b=100)
        )

        return html.Div(dcc.Graph(figure=fig), id=ids.COSTS_BAR_CHART)

    return html.Div(id=ids.COSTS_BAR_CHART)
