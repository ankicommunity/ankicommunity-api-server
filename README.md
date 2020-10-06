# djankiserv
`djankiserv` is an open source Django-based implementation of a synchronisation server for Anki 2.1+. It includes a user manager (the native Django user system).

Unlike the other popular open source Anki synchronisation server [`anki-sync-server`](https://github.com/ankicommunity/anki-sync-server), `djankiserv` stores the user data in a "proper" RDBMS. There are two 'database connections' that can be set - those for the 'system' (sessions, users, etc.) and those for user data. The 'system' stuff is just plain old Django, so any supported database can be used. The user data part currently uses either `postgresql` schemas or `mysql` databases, and currently only supports those two, though supporting other RDBMSes will definitely be considered later. `sqlite3` is an embedded database and works great for that. It is not appropriate for use in modern web applications in the opinion of the maintainer, so will never be supported by `djankiserv`.

There is a basic API for getting certain, per-user collection-related information (decks, deck configuration, models, tags) and also `notes` for a given user. It may evolve to include other functions, statistics and even doing cards, though the focus is currently on getting and maintaining proper synchronisation as well as the basic API for `notes`.

Limitations
===========

This is alpha software with some occasional data loss bugs. It works, sorta, if you hold it right. If it kills your kittens then you were forewarned!

Current known limitations (bugs!):

- it doesn't support abort and if it crashes in the middle of a sync then the server will have a corrupt view of the database. You should force an upload sync on next synchronisation if this ever happens!
- The v2 scheduler is not supported, and it is unclear how difficult this might be to implement.

Status
======
`djankiserv` is still alpha software. It was developed for the language learning platform [Transcrob.es](https://transcrob.es) and will mature as that project matures.

Installation
============
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

WARNING!!!

Recent `anki` clients now use 'chunking' and `Django` doesn't (appear to) support that out of the box, meaning you MUST have your site behind a proxy like `Apache` `mod_proxy` or `nginx`. Any site should have this anyway, so there likely won't be a strong push to implement this natively.

Kubernetes and docker
=====================
This repo also contains the `Dockerfile`s required to get it running and a `Kubernetes` helm chart. Docker images are currently being stored on the Docker Hub in `antonmelser/djankiserv` for both a working `djankiserv` and an `nginx`-based images containing the static files needed for the `admin` part in `antonmelser/djankiserv-static`.

The `helm` chart is known to work on `microk8s` and allows you to very easily install a full stack in a few commands, including SSL certificates for the synchronisation server (this is particularly important for `Ankidroid`). See the dedicated chart readme in `charts/README.md` of this repository for instructions installing the chart on a `microk8s` instance.

Configuration
=============

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

Connecting Anki to the sync server
==================================

The [Djankiserv Connect](https://ankiweb.net/shared/info/1724518526) Anki addon is available in the Anki addons repository. You can choose to sync all of your Anki profiles or just some (or none) of them with this plugin, and it is the recommended way of pointing your Anki desktop to Djankiserv.

Remember to close and open Anki again for the addon to be visible after plugin installation!

When you have installed the addon (see Anki docs for installing addons), simply go to Tools -> Preferences -> Network, then fill in the required fields, namely check the "Use custom sync server" and put in the server address (e.g., http://localhost:8002/djs/ or what ever it is available under).

You may also configure Anki Desktop without the plugin.

Recent versions of `Anki` desktop (2.1.32+ and maybe a bit earlier) now require you to use an environment variable to configure the sync server endpoints if you want to use a custom server. For Windows you can do the following (`powershell`):
```
PS C:\Users\your.user> $env:SYNC_ENDPOINT_MEDIA='http://localhost:8002/djs/msync/'; $env:SYNC_ENDPOINT='https://localhost:8002/djs/sync/'; & "C:\Program Files\Anki\anki.exe"; Remove-Item Env:\SYNC_ENDPOINT_MEDIA; Remove-Item Env:\SYNC_ENDPOINT
```
On Linux (assuming `anki` is in your path, which it should be. This may also work on Mac?):
```
SYNC_ENDPOINT_MEDIA='http://localhost:8002/djs/msync/' SYNC_ENDPOINT='http://localhost:8002/djs/sync/' anki
```

For `Ankidroid` you need to go to Settings -> Advanced -> Custom Sync Server and fill in both of the server endpoints, namely the sync URL (e.g., http://localhost:8002/djs/) and msync URL (e.g., http://localhost:8002/djs/msync/), but remember that Ankidroid now requires SSL so you will need to either use the supplied Kubernetes Helm Chart or create certificates using some other mechanism!

Development
===========

This implementation was initially developed in order to support the spaced repetition functionality for [`Transcrobes`](https://transcrob.es), an open source language learning platform/ecosystem. Any requests or functionality that don't interfere with using this project for that will definitely be entertained. Ideally the server would do everything that Ankiweb does, and much more. PRs are obviously always welcome!

If you want to get involved, start the conversation by creating an issue in the Github issue tracker for the functionality you are interest in.

`djankiserv` uses `poetry`:

`curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python`

Then just install the project:

`poetry install`

The settings will "just work" if you create a `postgresql`/`mysql` database called `djankiserv` with a superuser `djankiserv` with the password `password`.

You should then be able to launch by doing:

`poetry run ./scripts/runmanage.sh migrate`

`poetry run ./scripts/runmanage.sh createsuperuser`

And create yourself an admin user.

and finally:

`poetry run ./scripts/rundevserver.sh`

It will then be listening on `http://localhost:8002/`, and you can log into `http://localhost:8002/admin/` and add a normal user using the normal `django` web interface.

:warning::warning::warning: You MUST implement a proxy or certain sync functions WILL NOT WORK. A simple reverse proxy is all that you need, so any serious http server should be fine, and docs very easy to find.
