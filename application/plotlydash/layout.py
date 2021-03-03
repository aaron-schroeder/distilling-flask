import dash_bootstrap_components as dbc
import dash_html_components as html


# layout = html.Div(
LAYOUT = dbc.Container(
  [
    dbc.FormGroup(
      [
        dbc.Label('Select x-axis stream:'),
          dbc.RadioItems(
            options=[
              {'label': 'record', 'value': 'record'},
              {'label': 'time', 'value': 'time'},
              {'label': 'distance', 'value': 'distance'},
            ],
            value='record',
            id='x_stream',
            inline=True
          ),
      ]
    ),
    html.Div(id='figures'),
  ],
  id='dash-container',
  fluid=True,
)