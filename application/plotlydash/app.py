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
      'https://cdn.jsdelivr.net/gh/aaron-schroeder/distilling-flask@master'
      '/application/plotlydash/style.css',
      # Match the stylesheet used for Flask-generated pages.
      # TODO: Update to latest version.
      # 'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css
      # '/bootstrap.min.css',
    ],
    # Include my online assets folder, which contains a modified script
    # to make my programmatic hover-on-map stuff work.
    # NOTE: there must be a file in my local assets folder with the
    # same name as the corresponding online resource.
    # https://dash.plotly.com/external-resources'
    # '/load-assets-from-a-folder-hosted-on-a-cdn'
    assets_external_path='https://cdn.jsdelivr.net/gh/aaron-schroeder'
                         '/shared-assets@main/',
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