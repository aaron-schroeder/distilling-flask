from setuptools import find_packages, setup


setup(
  name='distilling-flask',
  version='0.1.0-alpha.1',
  description='TODO',
  url='https://github.com/aaron-schroeder/distilling-flask',
  author='Aaron Schroeder',
  author_email='aaron@trailzealot.com',
  license=None,
  packages=find_packages(exclude=['tests*']),
  install_requires=[
    'dash>=2.5.0',
    'dash-bootstrap-components>=1.0.0',
    'Flask>=2.1.0',
  ],
  entry_points={
    'console_scripts': [
      'df=distilling_flask.cli:cli',
      'dfc=distilling_flask.cli:context_cli'
    ],
  },
)
