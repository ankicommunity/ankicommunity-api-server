# Installation

See also: [Connecting Anki to the sync server](ConnectingAnki.md)

## Deployment as a Django app

`djankiserv` is a Django Rest Framework-based `Django` app, so can easily be used in any `postgresql`/`mysql`-driven `Django` site you already have. It is available in pypi, so you can simply install vi `pypi` and include as an app in your `INSTALLED_APPS`.

```
$ pip install djankiserv
```

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

```
# Djankiserv values

DATABASES = {}

if os.getenv("DJANKISERV_MAINDB_ENGINE") == "django.db.backends.mysql":
    DATABASES["default"] = {
        "ENGINE": os.getenv("DJANKISERV_MAINDB_ENGINE", "django.db.backends.mysql"),
        "NAME": os.getenv("DJANKISERV_MAINDB_NAME", "djankiserv"),
        "USER": os.getenv("DJANKISERV_MAINDB_USER", "djankiserv"),
        "PASSWORD": os.getenv("DJANKISERV_MAINDB_PASSWORD", "password"),
        "HOST": os.getenv("DJANKISERV_MAINDB_HOST", "127.0.0.1"),
        "OPTIONS": {"autocommit": True, "init_command": "SET default_storage_engine=INNODB"},
        "PORT": os.getenv("DJANKISERV_MAINDB_PORT", "3306"),
    }
else:
    DATABASES["default"] = {
        "ENGINE": os.getenv("DJANKISERV_MAINDB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DJANKISERV_MAINDB_NAME", "djankiserv"),
        "USER": os.getenv("DJANKISERV_MAINDB_USER", "djankiserv"),
        "PASSWORD": os.getenv("DJANKISERV_MAINDB_PASSWORD", "password"),
        "HOST": os.getenv("DJANKISERV_MAINDB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DJANKISERV_MAINDB_PORT", "5432"),
    }

if os.getenv("DJANKISERV_USERDB_ENGINE") == "django.db.backends.mysql":
    djankiserv.unki.AnkiDataModel = MariadbAnkiDataModel
    DATABASES["userdata"] = {
        "ENGINE": os.getenv("DJANKISERV_USERDB_ENGINE", "django.db.backends.mysql"),
        "NAME": os.getenv("DJANKISERV_USERDB_NAME", "djankiserv"),
        "USER": os.getenv("DJANKISERV_USERDB_USER", "djankiserv"),
        "PASSWORD": os.getenv("DJANKISERV_USERDB_PASSWORD", "password"),
        "HOST": os.getenv("DJANKISERV_USERDB_HOST", "127.0.0.1"),
        "OPTIONS": {
            "autocommit": True,
            "init_command": "SET default_storage_engine=INNODB",
            "sql_mode": "traditional,NO_BACKSLASH_ESCAPES",
        },
        "PORT": os.getenv("DJANKISERV_USERDB_PORT", "3306"),
    }
else:
    djankiserv.unki.AnkiDataModel = PostgresAnkiDataModel
    DATABASES["userdata"] = {
        "ENGINE": os.getenv("DJANKISERV_USERDB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DJANKISERV_USERDB_NAME", "djankiserv"),
        "USER": os.getenv("DJANKISERV_USERDB_USER", "djankiserv"),
        "PASSWORD": os.getenv("DJANKISERV_USERDB_PASSWORD", "password"),
        "HOST": os.getenv("DJANKISERV_USERDB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DJANKISERV_USERDB_PORT", "5432"),
    }


# You can remove the AUTHENTICATION_CLASSES that you don't want to support, or keep them all
# this better protects the /api/\* methods, the xSYNC methods have 'AllowAll' decorators
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}

# if you change this, it must also be changed in the images/static/Dockerfile
STATIC_ROOT = "build/static"

# This is required as Django will add a slash and redirect to that by default, and our clients don't
# support that
APPEND_SLASH = False

# this is not actually currently configurable, due to hardcoding in the clients
DJANKISERV_BASE_URL = "sync/"

# this is not actually configurable, due to hardcoding in the clients
DJANKISERV_BASE_MEDIA_URL = "msync/"

DJANKISERV_DATA_ROOT = os.getenv("DJANKISERV_DATA_ROOT", "/tmp")

# DEBUG STUFF
DJANKISERV_DEBUG = os.getenv("DJANKISERV_DEBUG", "False").lower() == "true"
DEBUG = DJANKISERV_DEBUG  # currently the same

DJANKISERV_GENERATE_TEST_ASSETS = False
DJANKISERV_GENERATE_TEST_ASSETS_DIR = "/tmp/asrv/"
```
