#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────
# FieldIQ Pro — One-command deploy script
# Usage: ./deploy.sh [dev|prod|stop|logs|rebuild]
# ────────────────────────────────────────────────────────────

set -e
COMPOSE="docker compose"

check_docker() {
  if ! command -v docker &>/dev/null; then
    echo "❌ Docker not found. Install from https://docs.docker.com/get-docker/"
    exit 1
  fi
  if ! docker info &>/dev/null; then
    echo "❌ Docker daemon not running. Start Docker and try again."
    exit 1
  fi
}

case "${1:-dev}" in

  dev)
    check_docker
    echo "🚀 Starting FieldIQ Pro in development mode..."
    [ ! -f .env ] && cp .env.example .env && echo "📋 Created .env from template — edit it if needed"
    $COMPOSE up --build -d
    echo ""
    echo "✅ FieldIQ Pro running:"
    echo "   Frontend  →  http://localhost"
    echo "   API Docs  →  http://localhost/docs"
    echo "   API Base  →  http://localhost/v1"
    echo ""
    echo "📋 Logs: ./deploy.sh logs"
    ;;

  prod)
    check_docker
    echo "🚀 Starting FieldIQ Pro in production mode..."
    [ ! -f .env ] && cp .env.example .env
    $COMPOSE -f docker-compose.yml up --build -d --remove-orphans
    echo "✅ Production deployment complete"
    ;;

  stop)
    echo "🛑 Stopping FieldIQ Pro..."
    $COMPOSE down
    echo "✅ Stopped"
    ;;

  rebuild)
    echo "♻️  Rebuilding all containers..."
    $COMPOSE down
    $COMPOSE build --no-cache
    $COMPOSE up -d
    echo "✅ Rebuild complete"
    ;;

  logs)
    $COMPOSE logs -f --tail=100
    ;;

  status)
    $COMPOSE ps
    ;;

  *)
    echo "Usage: $0 [dev|prod|stop|logs|rebuild|status]"
    exit 1
    ;;
esac
