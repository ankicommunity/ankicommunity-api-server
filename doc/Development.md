# Development

Any requests or functionality that don't interfere with using this project for that will definitely be entertained. Ideally the server would do everything that Ankiweb does, and much more. PRs are obviously always welcome!

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
