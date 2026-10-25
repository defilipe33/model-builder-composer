# WaterGEMS ModelBuilder Tool V3.3 — Map MVP

## UI
A divisória do painel de filtros agora é uma única linha contínua abaixo do
conjunto inteiro Campos/Editor.

## Mapa
A ação `Mapa` na toolbar alterna a área central entre:

- Tabela
- Mapa

### Navegação
- scroll do mouse: zoom;
- arraste: pan;
- Zoom +;
- Zoom -;
- Zoom Extents;
- Atualizar mapa.

### Geometria
Usa os WKB scenario-aware já existentes no WaterGEMS SQLite:
- Pipes -> LineString;
- nós, válvulas, tanques e bombas -> Point.

### Performance
A V3.3 NÃO cria um QGraphicsItem para cada elemento do modelo inteiro.

Contexto do mapa:
1. até 12.000 elementos amostrados uniformemente dos resultados atuais;
2. todos os elementos da página atual;
3. todos os elementos do SelectionSet.

Itens repetidos são eliminados.

Isso permite visualizar contexto e seleções sem tentar desenhar ~500k elementos
gráficos de uma vez.

### SelectionSet
Os elementos selecionados são destacados no mapa.
Mudanças de checkbox/página/SelectionSet atualizam o destaque.

### Clique no mapa
Clicar num elemento mostra `Tipo + ID` na barra de status.
Se o elemento estiver na página atual da tabela, a linha é selecionada e a
interface retorna para a tabela.

## Próximos passos
V3.4:
- seleção espacial por clique/retângulo/polígono;
- zoom para SelectionSet;
- filtros de camadas/tipos;
- labels condicionais por zoom.

V3.5:
- expansão conectada;
- upstream/downstream;
- N níveis;
- até reservatório/tanque/válvula.
