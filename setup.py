from setuptools import setup

setup(
    name="rockuefort",
    version="1.1",
    install_requires=[
        "docopt >=0.6.1",
        "mutagen >=1.27",
    ],
    scripts=["rockuefort"],
)
