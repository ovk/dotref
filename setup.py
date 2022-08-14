from setuptools import setup, find_packages
from dotref import __version__ as VERSION

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='dotref',
    version=VERSION,

    author='ovk',
    author_email='mail@okosh.xyz',

    description='Simple tool to manage dotfiles',
    long_description=long_description,
    long_description_content_type="text/markdown; variant=GFM",
    license='MIT',

    url='https://github.com/ovk/dotref',
    download_url = 'https://github.com/ovk/dotref/archive/v'+VERSION+'.tar.gz',
    project_urls={
        "Bug Tracker": "https://github.com/ovk/dotref/issues",
    },

    include_package_data=True,

    python_requires='>=3.6',
    classifiers=[
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
          ],

    keywords='dotfiles',
    packages=find_packages(exclude=['tests*']),

    extras_require={
        'test': ['coverage'],
    },

    entry_points={
        'console_scripts': [
            'dotref=dotref:main',
        ],
    }
)
