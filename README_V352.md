# WaterGEMS ModelBuilder Tool V3.5.2

Diagnóstico reforçado para SelectionSet -> Mapa.

## Garantia
`Atualizar mapa` e `Zoom Selection` consultam explicitamente todos os pares
tipo+ID do SelectionSet.

## Diagnóstico
Se um selecionado não produzir geometria WKB scenario-aware, `Zoom Selection`
agora informa:

- quantidade selecionada;
- quantidade sem geometria resolvida;
- primeiros tipo+ID que falharam.

Isso permite distinguir:
1. elemento não carregado no contexto;
2. elemento selecionado mas sem geometria resolvida no cenário.

## Visibilidade
`Zoom Selection` considera selecionados mesmo se a camada correspondente estiver
oculta ou se `Mostrar inativos` estiver desativado. Os selecionados são
temporariamente revelados para que a operação de zoom não falhe silenciosamente.
