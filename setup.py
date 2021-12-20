import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-freeipa-auth',
    version='2.0.2',
    packages=find_packages(),
    include_package_data=True,
    license='BSD License',
    description='A simple django freeipa rpc authentication backend app with a simple server failover solution.',
    long_description=README,
    tests_require=['pytest', 'pytest-django>=2.9.1,<=3.1.2', 'requests', 'Django >= 2.2.0'],
    install_requires=['requests', 'Django >= 2.2.0'],
    extras_require={
        'security': ['pyOpenSSL >= 0.14', 'cryptography>=1.3.4', 'idna>=2.0.0'],
    },
    author="Kris Anderson",
    author_email="kris@enervee.com",
    url="https://github.com/enervee/django-freeipa-auth",
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.9',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
