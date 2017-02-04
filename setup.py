from setuptools import find_packages, setup

setup(
    description='Work with music playlists written in a simple plaintext query format.',
    entry_points={
        'console_scripts': [
            'rockuefort=rockuefort:main',
        ],
    },
    install_requires=[
        'docopt >=0.6.1',
        'mutagen >=1.27',
    ],
    license='MIT',
    name='rockuefort',
    packages=find_packages(),
    url='https://github.com/kalgynirae/rockuefort',
    version='1.1',
)
