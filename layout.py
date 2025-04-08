from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

from . import capacities_bar_chart, energy_dropdown, ids
from . import costs_bar_chart, costs_pie_chart
from . import co2_demand_bar_chart, heat_demand_bar_chart, light_demand_bar_chart
from . import capacity_sliders  # Import the capacity_sliders module


def create_layout(app: Dash) -> html.Div:
    return html.Div(
        className="app-div",
        children=[
            html.H1(app.title),
            html.Hr(),

            # Energy source selection
            # html.Div(
            #     className="dropdown-container",
            #     children=[
            #         energy_dropdown.render(app),
            #     ],
            # ),

            # Interactive capacity explorer
            html.Div(
                className="interactive-capacity-section",
                style={"marginTop": "40px", "marginBottom": "40px", "backgroundColor": "#f8f9fa",
                       "padding": "20px", "borderRadius": "10px", "boxShadow": "0 4px 8px rgba(0,0,0,0.1)"},
                children=[
                    capacity_sliders.render(app),
                ]
            ),

            # Cost analysis section
            #
            # Demand analysis section
            html.Div(
                className="demand-analysis-section",
                style={"marginTop": "40px"},
                children=[
                    html.H2("Energy Demand Analysis", style={"marginBottom": "20px"}),

                    # Heat and Light demand row
                    html.Div(
                        className="demand-charts-row",
                        style={"display": "flex", "flexWrap": "wrap", "gap": "20px", "marginBottom": "30px"},
                        children=[
                            html.Div(
                                children=[
                                    html.H3("Heat Demand", style={"marginBottom": "10px"}),
                                    heat_demand_bar_chart.render_heat_demand(app),
                                ],
                                style={"flex": "1", "minWidth": "45%"}
                            ),
                            html.Div(
                                children=[
                                    html.H3("Light Demand", style={"marginBottom": "10px"}),
                                    light_demand_bar_chart.render_light_demand(app),
                                ],
                                style={"flex": "1", "minWidth": "45%"}
                            ),
                        ]
                    ),

                    # CO2 demand
                    html.Div(
                        className="co2-demand-section",
                        style={"marginTop": "20px"},
                        children=[
                            html.H3("CO2 Demand", style={"marginBottom": "10px"}),
                            co2_demand_bar_chart.render(app)
                        ]
                    )
                ]
            ),

            # Footer
            html.Div(
                className="footer",
                style={"marginTop": "50px", "borderTop": "1px solid #ddd", "paddingTop": "20px", "textAlign": "center"},
                children=[
                    html.P("Phoenix Williams - MEng Thesis - University of Galway - 2025",
                           style={"color": "#666", "fontSize": "0.9rem"})
                ]
            ),

            # Hidden div for storing the current page location - needed for callbacks
            dcc.Location(id=ids.PAGE_LOCATION, refresh=False)
        ],
    )
