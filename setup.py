from setuptools import setup, find_packages

setup(
    name='power_bi_analyzer',
    version='0.1.0',
    packages=find_packages(),
    author='Nokod Security',
    author_email='support@nokodsecurity.com',
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