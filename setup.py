from setuptools import setup, find_packages

extras_require = {
    "develop": [""]
}
extras_require["complete"] = sorted(set(sum(extras_require.values(), [])))

setup(
    name="stare",
    version="0.0.1",
    package_dir={"": "src"},
    packages=find_packages(where="src", exclude=["tests"]),
    description="",
    long_description="",
    url="https://giordonstark.com.com",
    author="Giordon Stark",
    author_email="gstark@cern.ch",
    license="BSD 3-clause",
    install_requires=[""],
    classifiers=["Development Status :: 1 - Planning"],
    extras_require=extras_require,
)
