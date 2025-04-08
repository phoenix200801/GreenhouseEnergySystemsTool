import plotly.express as px
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import pandas as pd
from . import ids

# Import demand data directly using the same approach as CO2 demand
import sys
sys.path.append(r"C:\Users\phoen\OneDrive - National University of Ireland, Galway\Masters\Thesis\Python Framework")
from Lib.InputCalculations import calculate_inputs
from Lib.HTCoefficients import calculate_htc
from Lib.HeatDemand import calculate_heatdemand
from Lib.LightDemand import calculate_lightdemand

# Get the data using the already defined imports
inputs_data = calculate_inputs()
htc = calculate_htc(inputs_data)
heat_demand = calculate_heatdemand(inputs_data, htc)
light_demand = calculate_lightdemand(inputs_data, htc, heat_demand)

def render_heat_demand(app: Dash) -> html.Div:
    @app.callback(
        Output(ids.HEAT_DEMAND_BAR_CHART, "children"),
        Input(ids.PAGE_LOCATION, "pathname"),
    )
    def update_heat_demand_chart(_) -> html.Div:
        try:
            # Use the heat demand data already calculated
            if heat_demand.empty or "QnetMWh" not in heat_demand.columns:
                return html.Div("No heat demand data available or missing 'QnetMWh' column.",
                                id=ids.HEAT_DEMAND_BAR_CHART)

            # Ensure index is datetime
            if not isinstance(heat_demand.index, pd.DatetimeIndex):
                return html.Div("Heat demand data index is not in datetime format.",
                                id=ids.HEAT_DEMAND_BAR_CHART)

            # Create month and year columns
            heat_demand_processed = heat_demand.copy()
            heat_demand_processed['Month'] = heat_demand_processed.index.strftime('%b %Y')
            heat_demand_processed['MonthNum'] = heat_demand_processed.index.year * 100 + heat_demand_processed.index.month

            # Group by month and calculate daily averages
            daily_avg_by_month = heat_demand_processed.groupby(['Month', 'MonthNum']).agg(
                AvgDailyHeatDemand=('QnetMWh', lambda x: x.sum() / (len(x) / 24))
                # Sum hourly values and divide by days
            ).reset_index()

            # Sort chronologically
            daily_avg_by_month = daily_avg_by_month.sort_values('MonthNum')

            # Create the bar chart
            fig = px.bar(
                daily_avg_by_month,
                x='Month',
                y='AvgDailyHeatDemand',
                title='Average Daily Heat Demand by Month',
                labels={'AvgDailyHeatDemand': 'Average Daily Heat Demand (MWh/day)', 'Month': 'Month'},
                category_orders={"Month": daily_avg_by_month['Month'].tolist()},
                color_discrete_sequence=['#FF5733']  # Orange/red color for heat
            )

            # Improve layout
            fig.update_layout(
                xaxis_tickangle=-45,
                yaxis_title="Average Daily Heat Demand (MWh/day)",
                xaxis_title="Month",
                plot_bgcolor='white',
                yaxis_gridcolor='lightgray',
                yaxis_tickformat=',.1f',
                margin=dict(t=50, b=100),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )

            return html.Div([
                dcc.Graph(figure=fig),
                html.Div([
                    html.H4("Heat Demand Summary Statistics", style={"marginTop": "20px"}),
                    html.Table([
                        html.Thead(
                            html.Tr([
                                html.Th("Metric", style={"textAlign": "left", "padding": "8px"}),
                                html.Th("Value", style={"textAlign": "right", "padding": "8px"})
                            ])
                        ),
                        html.Tbody([
                            html.Tr([
                                html.Td("Average Daily Demand", style={"padding": "8px"}),
                                html.Td(f"{heat_demand['QnetMWh'].sum() / (len(heat_demand) / 24):.2f} MWh/day",
                                        style={"textAlign": "right", "padding": "8px"})
                            ]),
                            html.Tr([
                                html.Td("Maximum Hourly Demand", style={"padding": "8px"}),
                                html.Td(f"{heat_demand['QnetMWh'].max():.2f} MWh",
                                        style={"textAlign": "right", "padding": "8px"})
                            ]),
                            html.Tr([
                                html.Td("Minimum Hourly Demand", style={"padding": "8px"}),
                                html.Td(f"{heat_demand['QnetMWh'].min():.2f} MWh",
                                        style={"textAlign": "right", "padding": "8px"})
                            ]),
                            html.Tr([
                                html.Td("Total Annual Demand", style={"padding": "8px"}),
                                html.Td(f"{heat_demand['QnetMWh'].sum():.2f} MWh",
                                        style={"textAlign": "right", "padding": "8px"})
                            ]),
                            html.Tr([
                                html.Td("Total Annual Demand", style={"padding": "8px"}),
                                html.Td(f"{heat_demand['QnetMWh'].sum() / 3600:.2f} MWh",
                                        style={"textAlign": "right", "padding": "8px"})
                            ])
                        ])
                    ], style={"width": "100%", "borderCollapse": "collapse", "marginTop": "10px"})
                ], style={"marginTop": "20px", "backgroundColor": "#f9f9f9", "padding": "15px", "borderRadius": "5px"})
            ], id=ids.HEAT_DEMAND_BAR_CHART)

        except Exception as e:
            return html.Div(f"Error processing heat demand data: {str(e)}",
                            id=ids.HEAT_DEMAND_BAR_CHART)

    return html.Div(id=ids.HEAT_DEMAND_BAR_CHART)