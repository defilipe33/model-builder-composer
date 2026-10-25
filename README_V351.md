# WaterGEMS ModelBuilder Tool V3.5.1

## Correção: SelectionSet -> Mapa

O SelectionSet continua sendo a fonte de verdade.

Agora, qualquer elemento selecionado por:

- tabela;
- checkbox;
- filtro;
- Selection Set do WaterGEMS;
- seleção espacial;
- expansão topológica;

é carregado incrementalmente no mapa caso sua geometria ainda não esteja
presente.

Isso evita depender da amostra de contexto do mapa.

## Zoom Selection

Antes de executar `Zoom Selection`, a aplicação:

1. lê todos os pares tipo+ID do SelectionSet;
2. compara com os itens já carregados no mapa;
3. busca somente as geometrias selecionadas ausentes;
4. acrescenta essas geometrias sem limpar o mapa ou alterar o viewport;
5. executa Zoom Selection.

Assim, um Pipe selecionado exclusivamente pela tabela também deve ser
localizado corretamente.

## Topologia

Upstream/downstream continuam exclusivamente topológicos:

```text
StartNode -> Pipe -> StopNode
```

Não são usados resultados hidráulicos ou sentido calculado de vazão.
