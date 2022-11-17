import math
import time

import pandas as pd

from power import adjusted_pace
# from application.plotlydash.dashboard_activity import calc_power


SPEED = 'speed'
GRADE = 'grade'

n_t = 60 * 60 * 3  # 3 hours in seconds
times = range(n_t)
df = pd.DataFrame.from_dict({
  'time': times,
  GRADE: [-4 * math.sin(0.01 * t) for t in times],
  SPEED: [3.0 + math.sin(0.1 * t) for t in times],
})

t1 = time.time()
df['equiv_speed'] = [adjusted_pace.equiv_flat_speed(s, g / 100) for s, g in zip(df[SPEED], df[GRADE])]
t2 = time.time()
df['NGP'] = [adjusted_pace.ngp(s, g / 100) for s, g in zip(df[SPEED], df[GRADE])]
t3 = time.time()
df['GAP'] = [adjusted_pace.gap(s, g / 100) for s, g in zip(df[SPEED], df[GRADE])]
t4 = time.time()

print(f'equiv_speed: {t2 - t1} sec')
print(f'NGP: {t3 - t2} sec')
print(f'GAP: {t4 - t3} sec')
