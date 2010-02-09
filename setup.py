from setuptools import setup


setup(
    name='test-utils',
    version='0.3',
    description='Grab bag of test utilities for Django & Jinja2 & Selenium.',
    long_description=open('README.rst').read(),
    author='Jeff Balogh',
    author_email='jbalogh@mozilla.com',
    url='http://github.com/jbalogh/test-utils',
    license='BSD',
    packages=['test_utils'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['nose'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        # I don't know what exactly this means, but why not?
        'Environment :: Web Environment :: Mozilla',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
