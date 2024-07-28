from setuptools import setup, find_packages

setup(
    name='power_bi_analyzer',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pb_analyzer=pb_analyzer.power_bi_embed_code_analyzer:main',
        ],
    },
    author='Amit Riftin',
    author_email='amit@nokodsecurity.com',
    description='A package to analyze Power BI embed codes.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/Nokod/PBAnalyzer',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)