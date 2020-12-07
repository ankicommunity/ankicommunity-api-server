# Development

Any requests or functionality that don't interfere with using this project for that will definitely be entertained. Ideally the server would do everything that Ankiweb does, and much more. PRs are obviously always welcome!

If you want to get involved, start the conversation by creating an issue in the Github issue tracker for the functionality you are interest in.

## Poetry

1. Install the dependency manager of the project first:

   ```
   curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3    
   ```

2. Install the dependencies of the project:

   ```
   poetry install
   ```

   > If you encounter a **SolveProblemError**, then you may try with updated dependencies:

   ```
   poetry update
   ```

The settings will "just work" if you create a `postgresql`/`mysql` database called `djankiserv` with a superuser `djankiserv` with the password `password`.

3. Migrate the database and create an admin account to get started:

   ```
   poetry run ./scripts/runmanage.sh migrate
   poetry run ./scripts/runmanage.sh createsuperuser
   ```

4. Run the server:

   ```
    poetry run ./scripts/rundevserver.sh
   ```

It will then be listening on `http://localhost:8002/`, and you can log into `http://localhost:8002/admin/` and add a normal user using the normal `django` web interface.
