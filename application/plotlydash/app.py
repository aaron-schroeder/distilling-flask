import dash
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc


def add_dashboard_to_flask(server):
  """Create a Plotly Dash dashboard with the specified server.

  This is actually used to create a dashboard that piggybacks on a
  Flask app, using that app its server.
  """
  dash_app = Dash(
    __name__,
    server=server,
    routes_pathname_prefix='/dash/',
    external_stylesheets=[
      # dbc.themes.BOOTSTRAP,
      # '/static/css/styles.css',  # Not yet.
      # Match the stylesheet used for Flask-generated pages.
      # TODO: Update to latest version.
      'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css',
    ],
    suppress_callback_exceptions=True,
    use_pages=True
  )

  dash_app.layout = html.Div([
    html.Nav(
      html.A('The Training Zealot Analysis Platform', href='/', className='navbar-brand'),
      className='navbar navbar-light bg-light'),

    dbc.Container(
      [
        html.Div(dcc.Link(
          f'{page["name"]} - {page["path"]}', href=page['relative_path']
        ))
        for page in dash.page_registry.values()
      ],
      fluid=True,
    ),

    html.Hr(),

    dash.page_container
  ])

  dash_app.enable_dev_tools(debug=True)

  return dash_app.server