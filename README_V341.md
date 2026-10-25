# WaterGEMS ModelBuilder Tool V3.4.1

## Desfazer seleção

O backend mantém até 30 snapshots recentes do SelectionSet.

O menu `Mapa` da toolbar contém:

- Mostrar mapa
- Atualizar mapa
- Atualizar região visível
- Zoom Extents
- Zoom Selection
- Modo Pan/clique
- Modo seleção por retângulo
- Modo seleção por polígono
- Desfazer última seleção

`Desfazer última seleção` restaura o SelectionSet imediatamente anterior e
sincroniza resumo, mapa e checkboxes da página atual.

## Atualização por região visível

Nova ação `Atualizar região visível`.

Ela usa a extensão atual do viewport e procura geometrias dos resultados atuais
que intersectam essa região.

Como o WaterGEMS SQLite analisado não expõe um índice espacial/RTree utilizável,
a V3.4.1 faz uma busca conservadora com limites:

- máximo de 10.000 geometrias examinadas;
- máximo de 12.000 geometrias encontradas;
- máximo de 2,5 segundos de processamento.

Se um limite é atingido antes da conclusão, o mapa atual permanece intacto e a
GUI informa:

> Não foi possível concluir a atualização regional porque foi atingido um limite
> de segurança. Aproxime mais o zoom ou aplique um filtro para reduzir a
> quantidade de elementos e tente novamente.

Isso evita varreduras longas que poderiam congelar a aplicação.

## Observação

Esta é uma primeira implementação sem índice espacial. Uma evolução futura pode
construir um índice espacial/cache próprio em background por modelo, permitindo
consultas de viewport muito mais completas e rápidas.
