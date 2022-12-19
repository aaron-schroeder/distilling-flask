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
    routes_pathname_prefix='/',
    external_stylesheets=[
      dbc.themes.BOOTSTRAP,
      # '/static/css/styles.css',  # Not yet.
      # Match the stylesheet used for Flask-generated pages.
      # TODO: Update to latest version.
      # 'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css',
    ],
    suppress_callback_exceptions=True,
    use_pages=True
  )

  dash_app.layout = html.Div([
    dbc.NavbarSimple(
      [
        dbc.NavItem(
          dbc.NavLink('Admin', href='/admin', external_link=True)
        )
      ],
      brand='The Training Zealot Analysis Platform',
      brand_href='/',
      # color='primary',
      # dark=True,
      # className='navbar navbar-light bg-light'
    ),
    dash.page_container
  ])

  dash_app.enable_dev_tools(debug=True)

  return dash_app.server