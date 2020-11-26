import os
from setuptools import setup, find_packages

extras_require = {
    'develop': [
        'pyflakes',
        'pytest',
        'pytest-cov',
        'pytest-mock',
        'coverage',
        'bumpversion',
        'pre-commit',
        'bandit',
        'black;python_version>="3.6"',  # Black is Python3 only
        'betamax',  # recording api calls for testing
        'betamax-serializers',
        'twine',  # uploading to pypi
    ]
}
extras_require['complete'] = sorted(set(sum(extras_require.values(), [])))

with open(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md'),
    encoding='utf-8',
) as readme_md:
    long_description = readme_md.read()


setup(
    name="stare",
    version="0.1.2",
    use_scm_version=lambda: {'local_scheme': lambda version: ''},
    package_dir={"": "src"},
    packages=find_packages(where="src", exclude=["tests"]),
    include_package_data=True,
    description="python sdk for Glance API",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://giordonstark.com",
    author="Giordon Stark",
    author_email="gstark@cern.ch",
    license="BSD 3-clause",
    install_requires=[
        'requests',  # for all HTTP calls to the API
        'cachecontrol[filecache]',  # for caching HTTP requests according to spec to local file
        'click>=6.0',  # for console scripts,
        'python-jose',  # for id token decoding
        'attrs',  # for model inflation/deflation
        'python-dotenv',  # for loading env variables
        'simple-settings',  # for handling settings more easily
    ],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    extras_require=extras_require,
    entry_points={'console_scripts': ['stare=stare.commandline:stare']},
    dependency_links=[],
)
