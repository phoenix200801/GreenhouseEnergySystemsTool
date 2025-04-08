import plotly.graph_objects as go
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import pandas as pd
from . import ids

# Import calculation functions
import sys
sys.path.append(r"C:\Users\phoen\OneDrive - National University of Ireland, Galway\Masters\Thesis\Python Framework")
from Lib.InputCalculations import calculate_inputs
from Lib.HTCoefficients import calculate_htc
from Lib.HeatDemand import calculate_heatdemand
from Lib.LightDemand import calculate_lightdemand
from Lib.CO2Demand import calculate_co2demand

def render(app: Dash) -> html.Div:
    @app.callback(
        Output(ids.CO2_DEMAND_BAR_CHART, "children"),
        Input(ids.PAGE_LOCATION, "pathname"),
    )
    def update_co2_demand_chart(_) -> html.Div:
        try:
            # Calculate all necessary data within the callback
            inputs_data = calculate_inputs()
            htc = calculate_htc(inputs_data)
            heat_demand = calculate_heatdemand(inputs_data, htc)
            light_demand = calculate_lightdemand(inputs_data, htc, heat_demand)
            co2_demand = calculate_co2demand(inputs_data, htc, heat_demand, light_demand)

            # Check if data exists
            if co2_demand.empty:
                return html.Div("No CO2 demand data available.", id=ids.CO2_DEMAND_BAR_CHART)

            # Check data validity before processing
            if "Total CO2 Demand" not in co2_demand.columns:
                return html.Div("Missing 'Total CO2 Demand' column in dataset.", id=ids.CO2_DEMAND_BAR_CHART)

            # Debug the data - look for invalid values
            if co2_demand["Total CO2 Demand"].isna().any():
                return html.Div("CO2 demand data contains NaN values.", id=ids.CO2_DEMAND_BAR_CHART)

            # Make a clean copy with proper datetime index
            co2_demand_processed = co2_demand.copy()
            co2_demand_processed.index = pd.to_datetime(co2_demand_processed.index)

            # Create month and sort columns with proper error checking
            co2_demand_processed['Month'] = co2_demand_processed.index.strftime('%b %Y')
            co2_demand_processed['SortKey'] = co2_demand_processed.index.map(lambda x: x.year * 100 + x.month)

            # Group data safely
            daily_avg_by_month = co2_demand_processed.groupby(['Month', 'SortKey'], as_index=False).agg(
                AvgDailyCO2Demand=('Total CO2 Demand', lambda x: x.sum() / (len(x) / 24) if len(x) > 0 else 0)
            )

            # Sort chronologically
            daily_avg_by_month = daily_avg_by_month.sort_values('SortKey')

            # Create figure using Graph Objects
            fig = go.Figure()

            # Add bar trace
            fig.add_trace(
                go.Bar(
                    x=daily_avg_by_month['Month'],
                    y=daily_avg_by_month['AvgDailyCO2Demand'],
                    marker_color='#2E8B57',
                    marker_line_color='#1a5336',
                    marker_line_width=1
                )
            )

            # Update layout
            fig.update_layout(
                title='Average Daily CO2 Demand by Month',
                xaxis_title='Month',
                yaxis_title='Average Daily CO2 Demand (kg/day)',
                xaxis_tickangle=-45,
                plot_bgcolor='white',
                showlegend=False,
                margin=dict(t=50, b=100),
                yaxis=dict(
                    gridcolor='lightgray',
                    tickformat=',.1f'
                )
            )

            return html.Div([
                dcc.Graph(figure=fig),
                html.Div([
                    html.H4("CO2 Demand Summary Statistics", style={"marginTop": "20px"}),
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
                                html.Td(f"{co2_demand['Total CO2 Demand'].sum() / (len(co2_demand) / 24):.2f} kg/day",
                                        style={"textAlign": "right", "padding": "8px"})
                            ]),
                            html.Tr([
                                html.Td("Maximum Hourly Demand", style={"padding": "8px"}),
                                html.Td(f"{co2_demand['Total CO2 Demand'].max():.2f} kg",
                                        style={"textAlign": "right", "padding": "8px"})
                            ]),
                            html.Tr([
                                html.Td("Minimum Hourly Demand", style={"padding": "8px"}),
                                html.Td(f"{co2_demand['Total CO2 Demand'].min():.2f} kg",
                                        style={"textAlign": "right", "padding": "8px"})
                            ]),
                            html.Tr([
                                html.Td("Total Annual Demand", style={"padding": "8px"}),
                                html.Td(f"{co2_demand['Total CO2 Demand'].sum():.2f} kg",
                                        style={"textAlign": "right", "padding": "8px"})
                            ])
                        ])
                    ], style={"width": "100%", "borderCollapse": "collapse", "marginTop": "10px"})
                ], style={"marginTop": "20px", "backgroundColor": "#f9f9f9", "padding": "15px", "borderRadius": "5px"})
            ], id=ids.CO2_DEMAND_BAR_CHART)

        except Exception as e:
            import traceback
            error_msg = f"Error processing CO2 demand data: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)  # Print to console for debugging
            return html.Div(f"Error processing CO2 demand data: {str(e)}",
                          id=ids.CO2_DEMAND_BAR_CHART)

    return html.Div(id=ids.CO2_DEMAND_BAR_CHART)
