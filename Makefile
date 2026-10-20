.PHONY: help install run start stop status service-install service-enable service-start service-stop service-status shortcut test

VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
DESKTOP_DIR := $(HOME)/Área de trabalho
SERVICE_DIR := $(HOME)/.config/systemd/user
SERVICE_NAME := manhua-manager.service

help:
	@echo "Comandos disponíveis:"
	@echo "  make install         - Cria venv e instala dependências"
	@echo "  make run             - Executa o servidor no terminal (foreground)"
	@echo "  make start           - Inicia o servidor em segundo plano"
	@echo "  make stop            - Para o servidor em segundo plano"
	@echo "  make status          - Verifica status do servidor"
	@echo "  make service-install - Instala o serviço systemd de usuário"
	@echo "  make service-enable  - Habilita inicialização automática com o sistema"
	@echo "  make service-start   - Inicia o serviço pelo systemd"
	@echo "  make service-stop    - Para o serviço pelo systemd"
	@echo "  make service-status  - Status do serviço no systemd"
	@echo "  make shortcut        - Cria o atalho na Área de Trabalho"
	@echo "  make test            - Roda os testes com pytest"

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install: $(VENV)/bin/activate
	$(PYTHON) generate_icons.py
	@chmod +x app.sh
	@echo "Instalação concluída com sucesso."

run: install
	$(PYTHON) server.py

start: install
	./app.sh start

stop:
	./app.sh stop

status:
	./app.sh status

service-install: install
	mkdir -p "$(SERVICE_DIR)"
	cp $(SERVICE_NAME) "$(SERVICE_DIR)/$(SERVICE_NAME)"
	systemctl --user daemon-reload
	@echo "Serviço instalado em $(SERVICE_DIR)/$(SERVICE_NAME)"

service-enable: service-install
	systemctl --user enable $(SERVICE_NAME)

service-start:
	systemctl --user start $(SERVICE_NAME)

service-stop:
	systemctl --user stop $(SERVICE_NAME)

service-status:
	systemctl --user status $(SERVICE_NAME)

shortcut:
	@mkdir -p "$(DESKTOP_DIR)"
	@cp -f manhua-tracker.desktop "$(DESKTOP_DIR)/manhua-tracker.desktop"
	@chmod +x "$(DESKTOP_DIR)/manhua-tracker.desktop"
	@echo "Atalho criado em: $(DESKTOP_DIR)/manhua-tracker.desktop"

test: install
	$(PYTEST) tests -v
