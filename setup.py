from setuptools import setup
import strconv

kwargs = {
    'py_modules': ['strconv'],
    'test_suite': 'test_strconv',
    'name': 'strconv',
    'version': strconv.__version__,
    'author': 'Byron Ruth, Shaswar Baban',
    'author_email': 'b@devel.io',
    'description': 'String type inference and conversion',
    'license': 'BSD',
    'keywords': 'types inference conversion strings',
    'url': 'https://github.com/shasthemass/strconv/',
    'classifiers': [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.9.10',
    ],
}

setup(**kwargs)
