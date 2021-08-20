import os

from setuptools import setup

base_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(base_dir, "VERSION")) as f:
    VERSION = f.read()

with open(os.path.join(base_dir, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

DESCRIPTION = "Unikube Django commons package."


setup(
    name="unikube-commons",
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    version=VERSION,
    install_requires=[
        "Django>=2.2,<3.0",
        "django-extensions>=3.1",
        "django-tenants>=3.2",
        "jwt>=1.1.0",
        "django-hurricane>0.5.0",
        "gitpython~=3.1.9",
        "pyyaml~=5.4.1",
        "python-keycloak-client~=0.2.3",
        "django-storages~=1.11",
        "django-storages[google]~=1.11",
        "boto3~=1.17",
    ],
    python_requires="~=3.8",
    packages=[
        "commons",
        "commons.amqp",
        "commons.graphql",
        "commons.helm",
        "commons.keycloak",
        "commons.keycloak.testing",
        "commons.middleware",
        "commons.management",
        "commons.management.commands",
    ],
    include_package_data=True,
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.0",
        "Framework :: Django :: 3.1",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
    ],
)
