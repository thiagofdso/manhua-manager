# Design Specification: Manhua Manager & Tracker

## 1. Overview
Manhua Manager é uma aplicação web leve e responsiva (com suporte a PWA) projetada para rastrear o progresso de leitura de manhuas/manhwas/mangás em notebooks e celulares conectados na mesma rede local (Wi-Fi). 

O sistema possui integração de serviço com o systemd em nível de usuário (`systemctl --user`), gerenciamento automatizado via `Makefile`, persistência em JSON (`database.json`) e atalho na Área de Trabalho para inicialização com um clique.

## 2. Requirements & Goals
- **Obra Inicial:** Iniciar o banco de dados com a obra **Overgeared**, capítulo atual 197 e template `https://manhuatop.org/manhua/overgeared-org/chapter-{chapter}/`.
- **Backend:** Servidor Flask leve em Python servindo a API REST e arquivos estáticos na porta `5000` (escutando em `0.0.0.0` para permitir acesso via IP de rede local).
- **Frontend & PWA:** Interface SPA em Vanilla HTML/CSS/JS moderna (tema escuro), Service Worker e Web App Manifest com ícones PNG válidos (192x192 e 512x512).
- **Systemd Integration:** Configurado como serviço de usuário em `~/.config/systemd/user/manhua-manager.service`, não exigindo `sudo` para gerenciamento.
- **Makefile:** Alvos para instalação (`make install`), execução manual (`make run`), inicialização em background (`make start` / `make stop`), instalação do serviço systemd (`make service-install`, `make service-start`, `make service-stop`), e instalação do atalho no desktop (`make shortcut`).
- **Atalho no Desktop:** Arquivo `.desktop` criado em `~/Área de trabalho/` com permissão de execução, que assegura que o servidor está em execução e abre `http://localhost:5000` no navegador padrão.

## 3. Architecture & Components

### 3.1 Files & Structure
```text
manhua-manager/
├── database.json              # Base de dados JSON persistida
├── server.py                  # API Flask e servidor estático
├── index.html                 # Interface web SPA do tracker
├── manifest.json              # Manifesto do PWA
├── sw.js                      # Service Worker PWA
├── icon-192.png               # Ícone PWA 192x192
├── icon-512.png               # Ícone PWA 512x512
├── requirements.txt           # Dependências Python: flask, flask-cors
├── manhua-manager.service     # Template da unidade de serviço systemd de usuário
├── Makefile                   # Regras de compilação, instalação e controle
└── docs/superpowers/specs/
    └── 2026-10-19-manhua-manager-design.md
```

### 3.2 Backend API (`server.py`)
- `GET /api/manhuas`: Retorna lista ordenada decrescente por `updatedAt`.
- `POST /api/manhuas`: Cria obra com `{ title, urlTemplate, currentChapter }`.
- `PATCH /api/manhuas/<id>`: Atualiza o capítulo via `{ chapter }` ou `{ delta: +1 | -1 }`. Garante `currentChapter >= 1`.
- `DELETE /api/manhuas/<id>`: Remove a obra da base.
- `GET /` e `GET /<path:filename>`: Serve o SPA e recursos estáticos do PWA.

### 3.3 Initial Database State (`database.json`)
```json
[
  {
    "id": 1,
    "title": "Overgeared",
    "urlTemplate": "https://manhuatop.org/manhua/overgeared-org/chapter-{chapter}/",
    "currentChapter": 197,
    "updatedAt": 1792454400
  }
]
```

### 3.4 Systemd Configuration (`manhua-manager.service`)
Salvo em `~/.config/systemd/user/manhua-manager.service`:
```ini
[Unit]
Description=Manhua Manager Tracker Service
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/Projetos/manhua-manager
ExecStart=%h/Projetos/manhua-manager/.venv/bin/python3 %h/Projetos/manhua-manager/server.py
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

### 3.5 Desktop Shortcut (`manhua-tracker.desktop`)
Salvo em `~/Área de trabalho/manhua-tracker.desktop` (e `~/.local/share/applications/` opcionalmente):
```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Manhua Tracker
Comment=Gerenciador de Manhuas e Leitura
Exec=sh -c "systemctl --user start manhua-manager.service || make -C %h/Projetos/manhua-manager start; while ! curl -s http://localhost:5000 >/dev/null; do sleep 0.3; done; xdg-open http://localhost:5000"
Icon=%h/Projetos/manhua-manager/icon-192.png
Terminal=false
Categories=Utility;Application;
```

## 4. Error Handling & Edge Cases
- **Conflito de Porta:** Caso a porta 5000 esteja ocupada, `server.py` ou o script de inicialização relatam erro claro nos logs do systemd (`journalctl --user -u manhua-manager`).
- **Validação de Capítulos:** Impossibilita capítulos negativos ou nulos (`currentChapter < 1`).
- **Inexistência de Arquivo de Banco:** Fallback transparente para recriação se o arquivo `database.json` for corrompido ou excluído.
- **Dependências no Linux:** Isolamento em ambiente virtual `.venv` para evitar restrições de `externally-managed-environment` do Python.

## 5. Verification Plan
1. **Ambiente e Instalação:** Testar `make install` criando `.venv` e instalando as bibliotecas.
2. **API & Endpoints:** Testar endpoints REST com `curl` (GET, POST, PATCH delta/capítulo, DELETE).
3. **PWA Assets:** Verificar resposta HTTP 200 para `index.html`, `manifest.json`, `sw.js`, `icon-192.png` e `icon-512.png`.
4. **Systemd Service:** 
   - `make service-install`
   - `make service-start`
   - `systemctl --user status manhua-manager.service` confirmando status `active (running)`.
   - `make service-stop` confirmando parada limpa.
5. **Desktop Shortcut:** Validar se o arquivo `~/Área de trabalho/manhua-tracker.desktop` tem permissão `chmod +x` e comando `xdg-open` configurado.
