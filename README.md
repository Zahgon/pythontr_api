# The Api of Pythontr.com

## We develop pythontr_api for pythontr.com

Pythontr Api is a django rest api project

## Development Notes

Start project on docker compose

Tips:

- docker compose run app sh -c "django-admin.py startproject app ." # Create project
- docker compose run app sh -c "mkdir core && touch core/__init__.py" # Create core
- docker compose run app sh -c "alembic revision --autogenerate -m 'change'" # Make migrations
- docker compose run app sh -c "python -c 'from app.db import new_session; from core.models import create_superuser; s=new_session(); create_superuser(s, \"admin@pythontr.com\", \"change-me\"); s.commit()'" # Create superuser
- docker compose run app sh -c "django-admin compilemessages" # Compile messages or

Single Test:


## Git Hooks Install for quality check on codes

- chmod u+x scripts/install-hooks.sh
- sh scripts/install-hooks.sh

# exec: "docker-credential-desktop.exe": executable file not found in $PATH

- vim ~/.docker/config.json
- rename credsStore to credStore
