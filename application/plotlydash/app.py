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
      dbc.icons.FONT_AWESOME,
      # Match the stylesheet used for Flask-generated pages.
      # TODO: Update to latest version.
      # 'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css
      # '/bootstrap.min.css',
    ],
    external_scripts=[
      # Include a modified plotly.js script to make my programmatic
      # hover-on-map stuff work.
      'https://cdn.jsdelivr.net/gh/aaron-schroeder/shared-assets@main/assets/'
      'plotly-strict-2.0.0-rc-adsmod.0.js',
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
      brand='Training Zealot Analysis Platform',
      brand_href='/',
      expand='xs',
      # color='primary',
      # dark=True,
      # className='navbar navbar-light bg-light'
    ),
    dash.page_container
  ])

  return dash_app.server