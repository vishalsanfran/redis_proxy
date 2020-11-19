DEPLOY_ENV ?= test
COMPOSE = docker-compose --env-file config/env.$(DEPLOY_ENV)
ACTIVATE = pipenv run

start_fg:
	$(COMPOSE) up

start:
	$(COMPOSE) up -d

restart: stop start

restart_fg: stop start_fg

stop:
	$(COMPOSE) down --remove-orphans

package:
	command -v pipenv || pip install pipenv
	pipenv install

test_only:
	-$(ACTIVATE) pytest test/

test: package restart test_only stop

shell: restart
	$(COMPOSE) exec web sh
	$(COMPOSE) down --remove-orphans