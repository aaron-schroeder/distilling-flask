```python
>>> for fname in glob.glob('*.pickle'):
>>>   with open(fname, 'rb') as f:
>>>     objs = []
>>>     while 1:
>>>         try:
>>>             objs.append(pickle.load(f))
>>>         except EOFError:
>>>             break
>>>     print(fname)
>>>     print(objs)

activities_3472157523_streams_time,latlng,distance,altitude,velocity_smooth,heartrate,cadence,watts,temp,moving,grade_smooth.pickle
[<Response [200]>]
athlete_activities.pickle
[<Response [200]>]
resp.pickle
[<Response [200]>]
requests.pickle
[]
activities_3472157523.pickle
[<Response [200]>]
token.pickle
[<Response [200]>, <Response [200]>, <Response [200]>, <Response [200]>, <Response [200]>, <Response [200]>]
```