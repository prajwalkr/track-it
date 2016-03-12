from setuptools import setup

setup(
  name = 'trackit',
  packages = ['trackit'],
  version = '0.2',
  description = 'Tracking APIs for couriers with major courier companies',
  author = 'K R Prajwal',
  author_email = 'prajwalrenukanand@gmail.com',
  url = 'https://github.com/prajwalkr/track-it', 
  download_url = 'https://github.com/prajwalkr/trackit/tarball/0.2', 
  keywords = ['couriers', 'tracking', 'api', 'courier-tracking'], 
  classifiers = [],
  install_requires=[
      "beautifulsoup4==4.4.1",
      "selenium==2.48.0",
      "requests==2.2.1",
      "python-dateutil==2.4.2",
  ]
)