from setuptools import setup

setup(
    name='html_generator',
    version='0.1',
    py_modules=['html_generator'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        html_generator=html_generator:cli
    ''',
)