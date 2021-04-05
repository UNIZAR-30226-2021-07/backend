from setuptools import find_packages, setup

install_requires = [
    "Flask-SQLAlchemy==2.4.4",
    "Flask==1.1.2",
    "Flask-Bcrypt==0.7.1",
    "gunicorn==20.0.4",
    "psycopg2-binary==2.8.6",
    "flask-jwt-extended==4.1.0",
    "flask-testing==0.8.0",
    "flask-socketio==5.0.1",
    "eventlet==0.30.2",
    "flask-session==0.3.2",
    "flask-cors==3.0.10",
]

extras_require = {
    "docs": {
        "Sphinx==3.5.2",
        "myst-parser==0.13.5",
    },
    "format": {
        "black",
        "isort",
        "flake8",
    },
}

setup(
    name="gatovid",
    version="0.1",
    packages=find_packages(exclude=("tests*", "dev*")),
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require=extras_require,
)
