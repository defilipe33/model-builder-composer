# WaterGEMS ModelBuilder Tool V3.4 — Spatial Selection

## Clique
No modo `Pan / clique`:

- clique simples: inspeciona/sincroniza com a tabela;
- Ctrl + clique: adiciona elemento ao SelectionSet;
- Shift + clique: remove elemento do SelectionSet.

## Retângulo e polígono
Modos do mapa:

- Selecionar por retângulo
- Selecionar por polígono

Ação:

- sem modificador: substitui o SelectionSet;
- Ctrl: adiciona;
- Shift: remove.

Polígono:
- clique esquerdo adiciona vértices;
- duplo clique, Enter ou botão direito finaliza;
- Esc cancela.

## Zoom
- Zoom +
- Zoom -
- Zoom Extents
- Zoom Selection

## Camadas
Menu `Camadas` permite mostrar/ocultar tipos individualmente:

- Pipe
- Junction
- PRV
- TCV
- Tank
- Pump
- etc.

## Atividade
Checkbox `Mostrar inativos`.

A geometria do mapa é enriquecida com `Core.IsActive` scenario-aware.

## SelectionSet
Toda seleção espacial usa o mesmo SelectionSet interno:
- não existem duplicatas;
- resumo é atualizado;
- destaque vermelho do mapa é atualizado;
- checkboxes da página atual são sincronizados.

## Performance
Mantém o contexto amostrado introduzido na V3.3:
- até 12.000 elementos do resultado atual;
- página inteira;
- todos os elementos selecionados.

A seleção espacial atua sobre o que está efetivamente carregado/visível no mapa.
