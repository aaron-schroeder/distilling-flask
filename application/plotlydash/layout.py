from dash import dcc, html
import dash_bootstrap_components as dbc


MAP_ID = 'map'
ELEVATION_ID = 'elevation'
SPEED_ID = 'speed'
POWER_ID = 'power'


COLORWAY = ['#636efa', '#EF553B', '#00cc96', '#ab63fa', '#FFA15A', '#19d3f3',
            '#FF6692', '#B6E880', '#FF97FF', '#FECB52']
COLORS = {
  'ATL': COLORWAY[1],
  'CTL': COLORWAY[0],
  'USERS': COLORWAY[2:]
}


def SettingsContainer(children, page_title=None):

  if page_title:
    # Convert `children` to a list (if it isn't already)
    # and insert a header element in the first position.
    main_children = [
      html.Div(
        html.H1(page_title, className='h2'),
        className='d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom',
      )
    ]
    if isinstance(children, list):
      main_children.extend(children)
    else:
      main_children.append(children)
  else:
    # Pass `children` to the layout as-is.
    main_children = children

  return dbc.Container(
    dbc.Row([
      dbc.Navbar(
        html.Div(
          html.Ul(
            [
              html.Li(
                dbc.NavLink(
                  [
                   html.Div(
                    html.I(className='fa-solid fa-gear'),
                    className='d-flex align-items-center me-2'
                   ),
                   html.Div('Profile Settings')
                  ],
                  href='/settings',
                  # href='/settings/user'  # or '/settings/profile'
                  class_name='d-flex',
                  active='exact',
                ),
                className='nav-item'
              ),
              html.Li(
                dbc.NavLink(
                  [
                   html.Div(
                    html.I(className='fa-solid fa-circle-nodes'),
                    className='d-flex align-items-center me-2'
                   ),
                   html.Div('Strava Account Connections')
                  ],
                  href='/settings/strava',
                  class_name='d-flex',
                  active='exact',
                ),
                className='nav-item'
              ),
              html.Li(
                dbc.NavLink(
                  [
                   html.Div(
                    html.I(className='fa-solid fa-microscope'),
                    className='d-flex align-items-center me-2'
                   ),
                   html.Div('Analyze Activity File')
                  ],
                  href='/analyze-file',
                  class_name='d-flex',
                  active='exact',
                ),
                className='nav-item'
              ),
            ],
            className='nav flex-column'
          ),
          className='sidebar-sticky'
        ),
        class_name='col-md-3 d-none d-md-block sidebar'  # 'navbar-light bg-light'
      ),
      
      html.Main(
        main_children,
        className='col-md-9 ms-sm-auto px-4',
        role='main',  # necessary?
      ),
    ]),
    fluid=True,
  )