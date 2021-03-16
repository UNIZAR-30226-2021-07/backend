from setuptools import find_packages, setup

install_requires = [
    "Flask-SQLAlchemy==2.4.4",
    "Flask==1.1.2",
    "gunicorn==20.0.4",
    "psycopg2-binary==2.8.6",
]

setup(
    name="gatovid",
    version="0.1",
    packages=find_packages(exclude=("tests*", "dev*")),
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    install_requires=install_requires,
)
