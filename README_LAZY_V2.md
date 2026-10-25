# Lazy Selection Engine + ModelBuilder Exporter V2

A abertura não extrai elementos. Apenas schema, cenários, alternativas e contexto do cenário são carregados.

Leves: `types`, `preview`, `select id`, `select label`.
Sob demanda: filtros scenario-aware e `dependencies`.
Pesados só por pedido explícito: `select type`, `extract-all`, `export`.

Execute: `python workflow_selection_lazy.py`
