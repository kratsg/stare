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

setup(
    name="stare",
    version="0.0.3",
    package_dir={"": "src"},
    packages=find_packages(where="src", exclude=["tests"]),
    description="",
    long_description="",
    url="https://giordonstark.com.com",
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
