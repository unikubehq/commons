<p align="center">
  <img src="https://raw.githubusercontent.com/unikubehq/commons/main/logo_commons.png" width="400">
</p>
<p align="center">
    <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black"></a>
    <a href="https://sonarcloud.io/dashboard?id=unikubehq_commons"><img src="https://sonarcloud.io/api/project_badges/measure?project=unikubehq_commons&metric=alert_status" alt="Quality Gate Status"></a>
    <a href="https://github.com/pre-commit/pre-commit"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" alt="pre-commit"></a>
    <a href="https://coveralls.io/github/unikubehq/commons?branch=main"><img src="https://coveralls.io/repos/github/unikubehq/commons/badge.svg?branch=main" alt="Coverage Status"></a>
    <img src="https://github.com/unikubehq/commons/actions/workflows/python-app.yaml/badge.svg" alt="Build Status">
</p>


# Unikube Commons

Commonly used code for unikube's backend services


## Automated testing
Make sure you apply all migrations with `python manage.py migrate` before running the tests.

Run tests with `python manage.py test`.

Local requirements:
* helm
