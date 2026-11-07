# Onça Guardiã

Agente de IA que lê notícias brasileiras toda semana e produz um relatório de riscos
ambientais e climáticos (queimadas, desmatamento, enchentes, seca, poluição) para cada
região do Brasil, usando um agente de IA com RAG sobre as notícias da semana e diretrizes
oficiais.

## Como rodar

Requisitos: [uv](https://docs.astral.sh/uv/) e Docker.

```bash
cp .env.example .env     # ajuste se necessário
uv sync
make up                  # sobe o Postgres com pgvector (porta 5433 por padrão)
uv run onca db ping      # deve imprimir "ok" e as versões
make check               # formatação, lint e testes
make down                # para o banco (make clean também apaga os dados)
```
