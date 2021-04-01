"""Default layout options for figures."""


LAT = 'lat'
LON = 'lon'
ELEVATION = 'elevation'
GRADE = 'grade'
SPEED = 'speed'
CADENCE = 'cadence'
HEARTRATE = 'heartrate'
POWER = 'power'


# XY_FIG_LAYOUT = dict(
#   height=190, # Too short. Make bigger.
#   legend=dict(yanchor='bottom', y=0.01),
# )


AXIS_LAYOUT = {

  ELEVATION: dict(
    # range=[
    #   math.floor(df[elev_lbl].min() / 200) * 200,
    #   math.ceil(df[elev_lbl].max() / 200) * 200
    # ],
    ticksuffix=' m',
    hoverformat='.2f',
  ),

  GRADE: dict(
    # Same values no matter if axis is primary or not.
    #title=dict(text='Grade (%)'),
    ticksuffix='%',
    range=[-75, 75],
    hoverformat='.2f',

    # Turn on the zeroline and make it visible in this color scheme.
    zeroline=True,
    zerolinewidth=1, 
    zerolinecolor='black',
  ),

  SPEED: dict(
    range=[-0.1, 6.0],
    ticksuffix=' m/s',
    hoverformat='.2f',

    # Turn on the zeroline and make it visible
    zeroline=True,
    zerolinewidth=1, 
    zerolinecolor='black',
  ),

  CADENCE: dict(
    # Same values no matter if axis is primary or not.
    ticksuffix=' spm',
    range=[110, 220],
    hoverformat='.0f',
  ),

  HEARTRATE: dict(
    ticksuffix=' bpm',
    range=[110, 170],
    hoverformat='.0f',
  ),

  POWER: dict(
    ticksuffix=' W/kg',
    hoverformat='.2f',
    #range=[-0.1, 35.0],
    #range=[9.0, 18.0],
    range=[-0.3, 18.0],
    zeroline=True,
    zerolinewidth=1, 
    zerolinecolor='black',
  ),

}


TRACE_LAYOUT = {

  ELEVATION: dict(
    mode='markers',
    marker=dict(size=3)
  ),

  SPEED: dict(
    line=dict(
      width=1,
    ),
    #opacity=0.7,
  ),

  CADENCE: dict(
    mode='markers',
    marker=dict(size=2)
  ),

  HEARTRATE: dict(
    line=dict(color='#d62728')
  ),

  POWER: dict(),

}

