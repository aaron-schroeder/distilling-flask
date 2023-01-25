import dash
from dash import Dash, html, Input, Output, State
import dash_bootstrap_components as dbc
from flask_login import current_user


NAVBAR_EXPAND = 'lg'


def add_dash_app_to_flask(server):
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
    dbc.Navbar(
      dbc.Container(
        [
          dbc.NavbarBrand(
            'Training Zealot Analysis Platform',
            href='/',
          ),
          dbc.NavbarToggler(
            id='navbar-toggler',
            n_clicks=0
          ),
          dbc.Collapse(
            dbc.Nav(
              [
                dbc.DropdownMenu(
                  [
                    # dbc.DropdownMenuItem("More pages", header=True),
                    dbc.DropdownMenuItem('Training Log', href='/', external_link=True),
                    dbc.DropdownMenuItem('Training Stress', href='/stress', external_link=True),
                    dbc.DropdownMenuItem('All Activities', href='/saved-list', external_link=True),
                  ],
                  nav=True,
                  in_navbar=True,
                  label='Training',
                  align_end=True,
                ),
                html.Div(id='nav-item-end'),
              ],
              navbar=True,
            ),
            id='navbarToggleContent',
            class_name='justify-content-end',
            is_open=False,
            navbar=True,
          )
        ],
        fluid=True,
      ),
      expand=NAVBAR_EXPAND,
      # className='navbar navbar-light bg-light'
      style={'box-shadow': 'inset 0 -1px 0 rgba(0, 0, 0, .1)'}
    ),
    dash.page_container
  ])

  # add callback for toggling the collapse on small screens
  @dash_app.callback(
    Output('navbarToggleContent', 'is_open'),
    Input('navbar-toggler', 'n_clicks'),
    State('navbarToggleContent', 'is_open'),
  )
  def toggle_navbar_collapse(n, is_open):
      if n:
          return not is_open
      return is_open

  # populate the navbar depending on user login status
  @dash_app.callback(
    Output('nav-item-end', 'children'),
    Input(dash.dash._ID_CONTENT, 'children')
  )
  def update_nav_item_end(_):
    if current_user.is_authenticated:
      return dbc.DropdownMenu(
        [
          dbc.DropdownMenuItem('Settings', href='/settings', external_link=True),
          dbc.DropdownMenuItem('Log Out', href='/logout', external_link=True),
        ],
        nav=True,
        in_navbar=True,
        label='User',
        align_end=True,
      )
    else:
      return dbc.Col(
        dbc.Button(
          'Log in',
          href='/login',
          color='primary',
          class_name=f'ms-0 ms-{NAVBAR_EXPAND}-2',
          size='sm'
        ),
        width='auto',
        class_name='d-flex align-items-center',
      )

  return dash_app