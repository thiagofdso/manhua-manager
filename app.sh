#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PID_FILE="$DIR/.server.pid"
LOG_FILE="$DIR/server.log"
PYTHON="$DIR/.venv/bin/python3"

if [ ! -f "$PYTHON" ]; then
    echo "Ambiente virtual não encontrado em $DIR/.venv. Execute 'make install' primeiro."
    exit 1
fi

is_running() {
    if [ -f "$PID_FILE" ]; then
        PID="$(cat "$PID_FILE" 2>/dev/null || true)"
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            return 0
        fi
    fi
    # Fallback: check if port 5000 is open by python in this dir
    PID="$(pgrep -f "$DIR/server.py" 2>/dev/null || true)"
    if [ -n "$PID" ]; then
        echo "$PID" > "$PID_FILE"
        return 0
    fi
    return 1
}

start_server() {
    if is_running; then
        echo "Manhua Manager já está em execução (PID: $(cat "$PID_FILE"))."
        return 0
    fi

    echo "Iniciando Manhua Manager em segundo plano..."
    nohup "$PYTHON" "$DIR/server.py" >> "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    
    # Wait up to 3 seconds for it to start
    for i in $(seq 1 15); do
        if curl -s http://localhost:5000/api/manhuas >/dev/null 2>&1; then
            echo "Manhua Manager iniciado com sucesso (PID: $PID) em http://localhost:5000"
            return 0
        fi
        sleep 0.2
    done

    if kill -0 "$PID" 2>/dev/null; then
        echo "Servidor iniciado (PID: $PID). Verifique os logs em $LOG_FILE se necessário."
    else
        echo "Falha ao iniciar o servidor. Verifique os logs em $LOG_FILE."
        rm -f "$PID_FILE"
        exit 1
    fi
}

stop_server() {
    if [ -f "$PID_FILE" ]; then
        PID="$(cat "$PID_FILE" 2>/dev/null || true)"
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            echo "Encerrando Manhua Manager (PID: $PID)..."
            kill "$PID" 2>/dev/null || true
            for i in $(seq 1 10); do
                if ! kill -0 "$PID" 2>/dev/null; then
                    break
                fi
                sleep 0.2
            done
            if kill -0 "$PID" 2>/dev/null; then
                kill -9 "$PID" 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
    fi

    # Cleanup any lingering instances of server.py from this directory
    LINGERING="$(pgrep -f "$DIR/server.py" 2>/dev/null || true)"
    if [ -n "$LINGERING" ]; then
        echo "Finalizando processos restantes: $LINGERING"
        kill -9 $LINGERING 2>/dev/null || true
    fi

    echo "Manhua Manager finalizado."
}

status_server() {
    if is_running; then
        echo "Manhua Manager está RODANDO (PID: $(cat "$PID_FILE")). Acesse: http://localhost:5000"
    else
        echo "Manhua Manager está PARADO."
    fi
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    status)
        status_server
        ;;
    run)
        echo "Iniciando em primeiro plano (Ctrl+C para sair)..."
        exec "$PYTHON" "$DIR/server.py"
        ;;
    *)
        echo "Uso: $0 {start|stop|status|run}"
        exit 1
        ;;
esac
