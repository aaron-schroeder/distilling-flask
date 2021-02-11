# strava_flask_dashboard

>Strava personal data display and analysis app, powered by Flask/Dash/Python.

[![License](http://img.shields.io/:license-mit-blue.svg)](http://badges.mit-license.org)

---

## Table of Contents                                                                    
- [Introduction](#introduction)
- [Dependencies and Installation](#dependencies-and-installation)
- [Examples](#example)<!-- - [Project Status](#project-status) -->
- [Contact](#contact)
- [License](#license)

---

## Introduction

Given a valid strava access token, the Flask app talks to Strava's API and 
displays running activities in a dashboard using plotly Dash.

I built this app so I could pick apart my raw Strava data, which includes
data streams for elevation, grade, and moving/stopped periods. In short,
I think Strava presents data in an unrealistically favorable way in its apps,
and I wanted to work with the raw feeds. There is power in looking at the
reality of things.

Over time, I generalized the Dash app to accept `pandas.DataFrame` as input. 
This meansyou can view any activity data you want, as long as it is formatted
correctly, using the `create_dashboard_df` function. This function has become 
the heart of the app, and it powers visualization of Strava data once the Flask
app converts it from json into a `pandas.DataFrame`.

Coming up, I'd like to set up pipelines that take running activity data from
a variety of sources and filetypes, and displays the time series in a common
interface. To that end, I've created a class to be used as column labels in
`pandas.DataFrame`. `StreamLabel` keeps track of both the field name and the
source of data streams. This facilitates a common, recognizable labeling
system for data streams stored in `DataFrame` columns. I've created custom 
accessors for `pandas.DataFrame` and `pandas.Index` to work with `StreamLabel`.

See the [Examples](#examples) section below to see how everything works.

---

## Dependencies and Installation

Flask, Dash, Dash Bootstrap Components, pandas, and requests are required.

Clone the repo:
```
git clone https://github.com/aaron-schroeder/strava_flask_dashboard.git
```

Change into the new directory and start a virtual environment. Then, install
the requirements:
```
pip install -r requirements.txt
```

You should be able to run the app now. See [Examples](#examples) below for more info.

---

## Examples

### Run the Flask app locally

```python
import os

# Get ahold of your strava access token
# (sorry, you are on your own for now)
# ...
os.environ['ACCESS_TOKEN'] = access_token

import application
app = application.create_app()
app.run()
```

### Run the Dash app with local data

From a saved strava json response from
`https://www.strava.com/api/v3/activities/${id}/streams/${fields}`:
```python
from application import create_dash_app_strava

fname = 'strava_stream_response.json'

app = create_dash_app_strava(fname)
```

From a `pandas.DataFrame`:
```python
import math
time = range(600)
df = pd.DataFrame.from_dict(dict(
    # Required fields:
    time=time,
    lat=[40.0 + 0.00001 * t for t in time],
    lon=[-105.0 + 0.00001 * t for t in time],
    elevation=[1609.0 + 40 * math.cos(0.01 * t) for t in time],
    speed=[3.0 + math.sin(0.1 * t) for t in time],
    # Optional fields:
    grade=[-4 * math.sin(0.01 * t) for t in time],
    heartrate=[140 + 15 * math.cos(0.1 * t) for t in time],
    cadence=[160 + 5 * math.sin(0.1 * t) for t in time],
))

# Drop any columns that lack data.
df = df.dropna(axis=1, how='all')

app = create_dash_app_df(df, 'fake')
app.run_server()
```

![The dashboard in action](https://github.com/aaron-schroeder/strava_flask_dashboard/blob/master/db_screenshot.jpg?raw=true)

### `StreamLabel` and custom accessors for `pandas` objects

Create a `DataFrame` where each row represents a record, and each column 
represents a data stream with a unique (field, source) id.
```python
import pandas as pd
from application.labels import StreamLabel

df = pd.DataFrame.from_dict({
    StreamLabel('time', 'strava'): [0, 1, 2, 3, 4, 5],
    StreamLabel('speed', 'strava'): [3.0, 3.2, 3.4, 3.6, 3.8, 3.6],
    StreamLabel('speed', 'garmin'): [2.9, 3.1, 3.3, 3.5, 3.7, 3.8],
})
```

Use the custom accessor to work with this specifically-formatted DataFrame.
```
>>> df.act.has_source('strava')
True

>>> df.act.has_source('device')
False

>>> df.act.source('strava')

   time (strava)  speed (strava)
0              0             3.0
1              1             3.2
2              2             3.4
3              3             3.6
4              4             3.8
5              5             3.6

>>> df.act.has_fields('speed', 'time')
True

>>> df.act.field('speed')

   speed (strava)  speed (garmin)
0             3.0             2.9
1             3.2             3.1
2             3.4             3.3
3             3.6             3.5
4             3.8             3.7
5             3.6             3.8
```

---

## Project Status

### Complete

### Current Activities

### Future Work

---

## Contact

You can get in touch with me at one of the following places:

[//]: # (- Website: <a href="https://trailzealot.com" target="_blank">trailzealot.com</a>)
- GitHub: <a href="https://github.com/aaron-schroeder" target="_blank">github.com/aaron-schroeder</a>
- LinkedIn: <a href="https://www.linkedin.com/in/aarondschroeder/" target="_blank">linkedin.com/in/aarondschroeder</a>
- Twitter: <a href="https://twitter.com/trailzealot" target="_blank">@trailzealot</a>
- Instagram: <a href="https://instagram.com/trailzealot" target="_blank">@trailzealot</a>

---

## License

[![License](http://img.shields.io/:license-mit-blue.svg)](http://badges.mit-license.org)

This project is licensed under the MIT License. See
[LICENSE](https://github.com/aaron-schroeder/strava_flask_dashboard/blob/master/LICENSE)
file for details.
