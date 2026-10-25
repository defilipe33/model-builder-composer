# WaterGEMS ModelBuilder Tool V3.3.1

Correções:

- corrigida regressão em `refresh_summary()` que fazia o painel SelectionSet
  permanecer vazio após qualquer seleção;
- resumo volta a atualizar por checkbox, seleção em massa, filtro, dependências
  e Selection Sets do WaterGEMS;
- mapa agora usa fundo cinza-escuro;
- elementos não selecionados: cinza-claro;
- elementos selecionados: vermelho, com espessura maior;
- nós selecionados também usam preenchimento vermelho;
- ação `Atualizar mapa` adicionada à toolbar;
- destaque do mapa é atualizado após carregar Selection Set, dependências e
  limpar seleção.
