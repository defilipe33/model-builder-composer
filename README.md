# Model Builder Composer

Aplicativo desktop em Python/PySide6 para inspecionar bancos SQLite do Bentley WaterGEMS e exportar elementos selecionados para planilhas ModelBuilder e camadas Shapefile.

## Recursos principais

- leitura *scenario-aware* de alternativas do WaterGEMS;
- seleção, filtros, mapa, pan/zoom e expansão topológica;
- diagnóstico de ilhas e qualidade de rede;
- exportação para Excel e Shapefile, preservando vértices de pipes;
- Customer Meters, demandas, padrões e elementos associados;
- perfis TXT de colunas para tabela, Excel e Shapefile.

## Requisitos

- Python 3.12 ou superior;
- dependências em `requirements.txt`.

```bash
python -m pip install -r requirements.txt
python app_gui.py
```

## Dados e privacidade

Este repositório contém somente o código-fonte. Bancos `.wtg.sqlite`, modelos WaterGEMS, backups, instaladores, exportações e arquivos temporários são deliberadamente ignorados pelo Git.

## Observação

O projeto interage com a estrutura SQLite de modelos WaterGEMS. A disponibilidade de tabelas e campos pode variar conforme a versão do WaterGEMS e o modelo utilizado.
