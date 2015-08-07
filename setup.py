'''
Created on Aug 6, 2015
@author: Jonas Wallin
'''
try:
	from setuptools import setup, Extension
except ImportError:
	try:
		from setuptools.core import setup, Extension
	except ImportError:
		from distutils.core import setup, Extension
		
metadata = dict(name='linkingEC2',
	packages         = ['linkingEC2'],
	package_dir      = {'linkingEC2': 'linkingEC2'},
	version          = '0.1',
	description      = 'wrapper for various ssh into EC2',
	author           = 'Jonas Wallin',
	maintainer_email = 'jonas.wallin81@gmail.com',
	url              = 'https://github.com/JonasWallin/linkingEC2',
	author_email     = 'jonas.wallin81@gmail.com',
	install_requires = ['boto'])
setup(**metadata)