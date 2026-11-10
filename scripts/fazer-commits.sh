#!/usr/bin/env bash
# Uso: bash scripts/fazer-commits.sh [N]  (sem N faz todos)
set -e
ONLY=$1
passo() { local n=$1 msg=$2; shift 2
  if [ -n "$ONLY" ] && [ "$ONLY" != "$n" ]; then return; fi
  git add -- "$@" && git diff --cached --quiet || git commit -m "$msg"; }
passo 1 "chore: inicializa projeto Python com dependências e configurações" requirements.txt .env.example .gitignore app/__init__.py tests/__init__.py eval/__init__.py
passo 2 "feat: classificação de problemas urbanos com CLIP (visão computacional)" app/visao.py
passo 3 "feat: geração de título, descrição e urgência com LLM local (Ollama)" app/geracao.py
passo 4 "feat: endpoint POST /classificar com validações e fluxo de confiança" app/main.py
passo 5 "test: testes de entrada inválida, baixa confiança e falha do LLM" tests
passo 6 "feat: script de avaliação com métricas e matriz de confusão" eval/avaliar.py eval/FONTES.md eval/dataset
passo 7 "docs: README com arquitetura, justificativas e limitações" README.md scripts/fazer-commits.sh
echo "Feito. Veja: git log --oneline"
