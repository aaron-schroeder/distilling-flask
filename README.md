# distilling-flask

>Personal running data display and analysis app, powered by Flask/Dash/Pandas.

[![License](http://img.shields.io/:license-mit-blue.svg)](http://badges.mit-license.org)

---

## Table of Contents                                                                    
- [Introduction](#introduction)
- [Dependencies and Installation](#dependencies-and-installation)
- [Examples](#example)<!-- - [Project Status](#project-status) -->
- [Testing](#testing)
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
This means you can view any activity data you want, as long as it is formatted
correctly, using the `create_dash_app` function.

If you have a valid Strava access token, you can view any of your Strava
runs in a dashboard powered by Plotly Dash. From there, you can save each
run to a local database, and view the long-term effects of training in a
training log dashboard.

See the [Examples](#examples) section below to see how everything works.

---

## Dependencies and Installation

Flask, Dash, Dash Bootstrap Components, pandas, and requests are required.

Clone the repo:
```
git clone https://github.com/aaron-schroeder/distilling-flask.git
```

Change into the new directory and start a virtual environment. Then, install
the requirements:
```
pip install -r requirements.txt
```

You should be able to run the app now. See [Examples](#examples) below for more info.

---

## Examples

### Run the Flask app locally with a Strava access token

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
![List of activities](https://github.com/aaron-schroeder/distilling-flask/blob/master/images/activity_list_screenshot.jpg?raw=true)

![Saved activities in training log dashboard](https://github.com/aaron-schroeder/distilling-flask/blob/master/images/training_log_screenshot.jpg?raw=true)

### Run the Dash app with an uploaded file

Options:
  - `json` file containing response from `https://www.strava.com/api/v3/activities/${athlete_id}/streams/${fields}`
  - `fit` file (requires [`fitparse`](https://github.com/dtcooper/python-fitparse) and [`dateutil`](https://dateutil.readthedocs.io/en/stable/))
  - `csv` file (requires expected column naming convention, see below)
  - `tcx` file (requires [`activereader`](https://github.com/aaron-schroeder/activereader))
  - `gpx` file (requires [`activereader`](https://github.com/aaron-schroeder/activereader))
  <!--
  - `csv` file from Wahoo Fitness (WIP) 
  -->
```python
from application.plotlydash.dashboard_upload import create_dash_app

app = create_dash_app()
app.run_server()
```

From a `pandas.DataFrame` (use these exact column names):
```python
import math
import pandas as pd

from application.plotlydash.dashboard_activity import create_dash_app

time = range(600)
df = pd.DataFrame.from_dict(dict(
    time=time,
    lat=[40.0 + 0.00001 * t for t in time],
    lon=[-105.0 + 0.00001 * t for t in time],
    elevation=[1609.0 + 40 * math.cos(0.01 * t) for t in time],
    grade=[-4 * math.sin(0.01 * t) for t in time],
    speed=[3.0 + math.sin(0.1 * t) for t in time],
    distance=[3.0 * t + 10 * math.cos(0.1 * t) for t in time],
    heartrate=[140 + 15 * math.cos(0.1 * t) for t in time],
    cadence=[160 + 5 * math.sin(0.1 * t) for t in time],
))

# (if needed) Drop any columns that lack data.
df = df.dropna(axis=1, how='all')

app = create_dash_app(df)

app.run_server()
```

![The dashboard in action](https://github.com/aaron-schroeder/distilling-flask/blob/master/images/db_screenshot.jpg?raw=true)

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
>>> df.sl.has_source('strava')
True

>>> df.sl.has_source('device')
False

>>> df.sl.source('strava')

   time (strava)  speed (strava)
0              0             3.0
1              1             3.2
2              2             3.4
3              3             3.6
4              4             3.8
5              5             3.6

>>> df.sl.has_fields('speed', 'time')
True

>>> df.sl.field('speed')

   speed (strava)  speed (garmin)
0             3.0             2.9
1             3.2             3.1
2             3.4             3.3
3             3.6             3.5
4             3.8             3.7
5             3.6             3.8

>>> StreamLabel.from_str('speed~new_src')
speed (new_src)
```

---

## Testing

### Functional testing

This requires user-supplied files: `client_secrets.json` and `tokens.json`.

```sh
pip install -r requirements_dev.txt
python -m unittest discover -p test_*.py application.functional_tests
```

### Unit testing
```sh
python -m unittest discover -p test_*.py application.tests
```

## Project Status

### Current Activities

The Flask app is becoming a full-fledged training log. Strava activities
can be viewed in a dashboard and saved to a database, and soon uploaded
files will be saveable too. The long-term effects of training can be 
visualized in a training log dashboard, which is still evolving.

### Future Work

Coming up, I'd like to set up pipelines that take running activity data from
a variety of sources and filetypes, and displays the time series in a common
interface. To that end, I've created a class to be used as column labels in
`pandas.DataFrame`. `StreamLabel` keeps track of both the field name and the
source of data streams. This facilitates a common, recognizable labeling
system for data streams stored in `DataFrame` columns. I've created custom 
accessors for `pandas.DataFrame` and `pandas.Index` to work with `StreamLabel`.

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
[LICENSE](https://github.com/aaron-schroeder/distilling-flask/blob/master/LICENSE)
file for details.
