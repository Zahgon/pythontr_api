# The Api of Pythontr.com

## We develop pythontr_api for pythontr.com

Pythontr Api is a flask rest api project

## Development Notes

Start project on docker compose

Tips:

- docker compose run app sh -c "python manage.py db migrate" # Make migrations
- docker compose run app sh -c "python manage.py db upgrade" # Apply migrations
- docker compose run app sh -c "python manage.py wait-for-db" # Wait for the db
- docker compose run app sh -c "pytest && flake8" # Test
- docker compose run app sh -c "TEST_DATABASE_URL=$DB_URL pytest" # Test on the db server
- docker compose run app sh -c "pybabel compile -d locale" # Compile messages

Single Test:

- docker compose run app sh -c "pytest user/admin/tests/test_user_admin_api.py::UserAdminAPITests::test_list_users"

## Git Hooks Install for quality check on codes

- chmod u+x scripts/install-hooks.sh
- sh scripts/install-hooks.sh

# exec: "docker-credential-desktop.exe": executable file not found in $PATH

- vim ~/.docker/config.json
- rename credsStore to credStore
