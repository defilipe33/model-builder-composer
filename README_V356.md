# WaterGEMS ModelBuilder Tool V3.5.6 — Diagnóstico geométrico

## Novas colunas Geometry para Pipe

- Geometry.Length
- Geometry.IsZeroLength
- Geometry.HasCoincidentEndpoints
- Geometry.DiagnosticStatus

Também continuam disponíveis:
- Geometry.VertexCount
- Geometry.StartNodeID / StopNodeID
- Geometry.StartX / StartY
- Geometry.StopX / StopY

`Geometry.Length` é o comprimento da LineString armazenada no modelo.
Na interface ele respeita SI/US.

## Tolerância

Para diagnóstico de comprimento zero / extremos coincidentes foi adotada
tolerância de 1 mm.

Isso evita exigir igualdade binária perfeita de coordenadas.

## Símbolo de Pipe com comprimento zero

Um Pipe cuja geometria tenha comprimento <= 1 mm deixa de desaparecer no mapa.

Ele é desenhado como:
- círculo com X no centro;
- tamanho fixo na tela;
- âmbar quando não selecionado;
- vermelho quando selecionado.

O tooltip informa que o Pipe possui comprimento geométrico aproximadamente zero.

## Nós coincidentes

Quando dois ou mais elementos nodais carregados no mapa ocupam a mesma
coordenada (tolerância de 1 mm), o mapa desenha um anel tracejado ao redor do
ponto.

O tooltip do anel informa:
- quantidade de nós coincidentes;
- tipos e IDs dos primeiros elementos.

Esse overlay é apenas diagnóstico visual e não altera SelectionSet, exportação
ou banco WaterGEMS.
