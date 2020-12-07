# Installation

See also: [Connecting Anki to the sync server](ConnectingAnki.md)

## Deployment as a Django app

`djankiserv` is a Django Rest Framework-based `Django` app, so can easily be used in any `postgresql`/`mysql`-driven `Django` site you already have. It is available in pypi, so you can simply install vi `pypi` and include as an app in your `INSTALLED_APPS`.

```
$ pip install djankiserv
```
This will not install a database driver. You may pull in a supported database driver by adding an extra to the `pip` install(`mysql` and `pgsql` are supported):
```
$ pip install djankiserv[pgsql]
```
Which will also install `psycopg2-binary`. If you choose `mysql`, you will also need to have the `mysql` development headers, so that `pip` can build the driver (tested with `libmariadb-dev` on Ubuntu/Debian).

```
INSTALLED_APPS = [
    # core required
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    ...
    "rest_framework",  # DRF IS ALSO REQUIRED!
    "djankiserv.apps.DjankiservConfig",
    ...
]
```

## Deployment with Kubernetes and Docker

The `helm` chart is known to work on `microk8s` and allows you to very easily install a full stack in a few commands, including SSL certificates for the synchronisation server (this is particularly important for `Ankidroid`). See the dedicated chart readme in `charts/README.md` of this repository for instructions installing the chart on a `microk8s` instance.

## Working around chunking with a proxy

You need to implement a proxy or certain sync functions *will not work*.

Recent `anki` clients now use a mechanism called 'chunking' and `Django` doesn't (appear to) support that out of the box, meaning you MUST have your site behind a proxy like `Apache` `mod_proxy` or `nginx`. Any site should have this anyway, so there likely won't be a strong push to implement this natively.

# Configuration

This repo contains the `Django` project which is used for the `Kubernetes Helm` chart, so you can see all the required options in that file in `djankiserv/src/djankiservproj/settings.py`. Sensible defaults should exist for all options, and all of the options that make sense to change via environment variables are configurable in that way.

These environment variables are also stated below.

## Main database connection data

| Variable                     | Default                    | Comment            |
|:----------------------------:|:--------------------------:|--------------------|
| `DJANKISERV_MAINDB_ENGINE`   | `django.db.backends.mysql` | `django.db.backends.postgresql` |
| `DJANKISERV_MAINDB_NAME`     | djankiserv	||
| `DJANKISERV_MAINDB_USER`     | djankiserv ||
| `DJANKISERV_MAINDB_PASSWORD` | password ||
| `DJANKISERV_MAINDB_HOST`     | `127.0.0.1` ||
| `DJANKISERV_MAINDB_PORT`     | `3306` (MySQL) or `5432` (PostgreSQL) ||

## User database connection data

| Variable                     | Default                    | Comment            |
|:----------------------------:|:--------------------------:|--------------------|
| `DJANKISERV_USERDB_ENGINE`   | `django.db.backends.mysql` | `django.db.backends.postgresql` |
| `DJANKISERV_USERDB_NAME`     | djankiserv	||
| `DJANKISERV_USERDB_USER`     | djankiserv ||
| `DJANKISERV_USERDB_PASSWORD` | password ||
| `DJANKISERV_USERDB_HOST`     | `127.0.0.1` ||
| `DJANKISERV_USERDB_PORT`     | `3306` (MySQL) or `5432` (PostgreSQL) ||

## Miscellaneous options

| Variable                     | Default                    | Comment            |
|:----------------------------:|:--------------------------:|--------------------|
| `DJANKISERV_DEBUG`           | `False` ||
| `DJANKISERV_DATA_ROOT`       | `/tmp` ||
