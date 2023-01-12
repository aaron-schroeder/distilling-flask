# distilling-flask

>Personal running data display and analysis app, powered by Flask/Dash/Pandas.

[![License](http://img.shields.io/:license-mit-blue.svg)](http://badges.mit-license.org)

---

## Table of Contents                                                                    
- [Introduction](#introduction)
- [Dependencies and Installation](#dependencies-and-installation)
- [Running the App](#running-the-app)<!-- - [Project Status](#project-status) -->
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

See the [Running the App](#running-the-app) below to see how everything works.

---

## Dependencies and Installation

Check out [the requirements file](requirements.txt) to see all dependencies.

### Python IDE

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

### Docker container

Create an image by running the following command in the same dir as `Dockerfile`: 
```sh
docker build -t distillingflask:latest .
```

Create and start a container from the image with
```sh
docker run --name distillingflask  \
    -e MODULE_NAME=application.app  \
    -e VARIABLE_NAME=server  \
    -e STRAVA_CLIENT_ID=<client id>  \
    -e STRAVA_CLIENT_SECRET=<client secret>  \
    -e PASSWORD=<password>  \
    -d  \
    -p 5000:80  \
    --rm  \
    distillingflask:latest
```

## Running the App

### Locally

#### Strava-connected, with your Strava app client id and client secret

This option pretty much gets you the full-blown app running on your local machine.
You can now authorize the app to use the data from your Strava account.

To do this, you must:
- Create your own API application [on Strava's website](https://www.strava.com/settings/api)
- Within the ["My API application"](https://www.strava.com/settings/api)
  section of your Strava settings:
  - Set the authorization callback domain for your app to `localhost`
  - Copy your app's "client ID" and "client secret" somewhere secure

To run the app from a python script:
```python
import os

import application


# Get ahold of the credentials for your Strava app
# ...
os.environ['STRAVA_CLIENT_ID'] = client_id
os.environ['STRAVA_CLIENT_SECRET'] = client_secret

# Choose the password for this app. Ideally don't use your Strava password.
os.environ['PASSWORD'] = 'super_secret_password'
app = application.create_app()
app.run()
```
To run the app from the command line:
```
STRAVA_CLIENT_ID=${STRAVA_CLIENT_ID}  \
STRAVA_CLIENT_SECRET=${STRAVA_CLIENT_SECRET}  \
PASSWORD=super_secret_password  \
flask --app application
```

![List of activities](https://github.com/aaron-schroeder/distilling-flask/blob/master/images/activity_list_screenshot.jpg?raw=true)

![Saved activities in training log dashboard](https://github.com/aaron-schroeder/distilling-flask/blob/master/images/training_log_screenshot.jpg?raw=true)

#### Strava-disconnected, allowing a subset of features.

You don't need to set your app up with Strava to access some of
its features like the file upload analysis dashboard.
The command to run this configuration of the app is simpler.

Python script:
```python
import os

import application


# Choose the password for this app. Ideally don't use your Strava password.
os.environ['PASSWORD'] = 'super_secret_password'
app = application.create_app()
app.run()
```
Command line:
```sh
PASSWORD=super_secret_password  \
flask --app application
```

Filetypes accepted by the upload-to-analyze dashboard:
  - `fit` file (requires [`fitparse`](https://github.com/dtcooper/python-fitparse) and [`dateutil`](https://dateutil.readthedocs.io/en/stable/))
  - `tcx` file (requires [`activereader`](https://github.com/aaron-schroeder/activereader))
  - `gpx` file (requires [`activereader`](https://github.com/aaron-schroeder/activereader))
  - `csv` file (requires that headers adhere to [the naming convention defined
    by the application](application/plotlydash/figure_layout.py#L4-L11))
  <!--
  - `csv` file from Wahoo Fitness (WIP) 
  -->

![The dashboard in action](https://github.com/aaron-schroeder/distilling-flask/blob/master/images/db_screenshot.jpg?raw=true)

### Production

To create an instance of the app with production-oriented settings, pass
the value `prod` to the `config_name` keyword of `create_app()`.

Like the development configuration, the production configuration of 
defaults to using an on-disk SQLite database, or any database 
specified by the `DATABASE_URL` environment variable
(including in-memory SQLite with the url `sqlite://`)

The production configuration also allows for the use of a PostgreSQL database
if the right environment variables (starting with `POSTGRES_`) are set.

```
SECRET_KEY=random_secret_key  \
STRAVA_CLIENT_ID=00000  \
STRAVA_CLIENT_SECRET=gobbledygoop  \
POSTGRES_DB=db_name  \
POSTGRES_PORT=5432  \
POSTGRES_USER=user  \
POSTGRES_PW=password  \
POSTGRES_URL=dburl.example.com  \
flask --app "application:create_app('prod')"
```

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

This requires user-supplied files in the following locations:
  - `client_secrets.json`
  - `tests/functional_tests/strava_credentials.json`

```sh
pip install -r requirements_dev.txt
python -m unittest discover -p test_*.py tests.functional_tests
```

### Unit testing
```sh
python -m unittest discover -p test_*.py tests.unit_tests
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
