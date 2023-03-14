from setuptools import find_packages, setup


setup(
  name='distilling-flask',
  version='0.1.0-alpha.1',
  description='TODO',
  url='https://github.com/aaron-schroeder/distilling-flask',
  author='Aaron Schroeder',
  author_email='aaron@trailzealot.com',
  license=None,
  packages=find_packages(),
  install_requires=[
    'Flask>=2.1.0',
  ],
  entry_points={
    'console_scripts': [
      'df=application.cli:cli',
    ],
  },
)
