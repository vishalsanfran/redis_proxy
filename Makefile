DEPLOY_ENV ?= test
COMPOSE = docker-compose --env-file config/env.$(DEPLOY_ENV)
COMPOSE_RESP = $(COMPOSE) -f docker-compose.resp.yml
ACTIVATE = pipenv run

start_fg:
	$(COMPOSE) up

start:
	$(COMPOSE) up -d

start_resp:
	$(COMPOSE_RESP) up -d

start_resp_fg:
	$(COMPOSE_RESP) up

restart: stop start

restart_resp: stop_resp start_resp

restart_fg: stop start_fg

stop:
	$(COMPOSE) down --remove-orphans

stop_resp:
	$(COMPOSE_RESP) down --remove-orphans

package:
	command -v pipenv || pip install pipenv
	pipenv install

test_only:
	-$(ACTIVATE) pytest test/

test_only_resp:
	-$(ACTIVATE) pytest test_resp/

test: package restart test_only stop restart_resp test_only_resp stop_resp

shell_only:
	$(COMPOSE) exec web sh

shell_only_resp:
	$(COMPOSE_RESP) exec web_resp sh

shell: restart shell_only stop

shell_resp: restart_resp shell_only_resp stop_resp