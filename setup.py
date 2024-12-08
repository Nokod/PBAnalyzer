from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='power_bi_analyzer',
    version='1.0.2',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'public-reports-analyzer=pb_analyzer.power_bi_public_report_analyzer:main',
            'shared-reports-analyzer=pb_analyzer.power_bi_shared_reports_analyzer:main',
        ]
    },
    author='Nokod Security',
    author_email='support@nokodsecurity.com',
    description='A package to analyze Power BI reports.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/Nokod/PBAnalyzer',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=required,
)
