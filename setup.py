from setuptools import find_packages, setup


setup(
  name='distilling-flask',
  packages=find_packages(),
  # ....
  entry_points={
    'console_scripts': [
      'df=application.cli:cli',
    ],
  },
)
