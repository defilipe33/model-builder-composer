# WaterGEMS Lazy Selection + ModelBuilder Exporter V2.2

Esta versão reúne:

- robustez de entrada;
- extração realmente seletiva;
- Network Topology Resolver.

## Network Topology Resolver

Para cada Pipe, os endpoints são resolvidos por prioridade:

1. `BaseLink_HMIDataSetTopology_Data`;
2. `BaseDirectedNode_HMIDataSetTopology_Data.HMITopologyDownstreamLinkID`;
3. geometria do Pipe versus geometria dos nós.

A exportação inclui:

- `StartNodeLabel`
- `StopNodeLabel`
- `StartNodeSourceID`
- `StopNodeSourceID`
- `StartNodeResolution`
- `StopNodeResolution`

Valores possíveis de resolução incluem:

- `BaseLink`
- `DirectedNode.DownstreamLinkID`
- `Geometry`
- `Geometry+DirectedNode`
- `Geometry(non-directed preferred)`
- `Unresolved`

## Dependencies

O comando `dependencies` agora usa o mesmo resolver topológico.
Assim, se um endpoint não vier diretamente do `BaseLink`, o programa ainda tenta
identificá-lo por DirectedNode ou geometria antes de adicionar o nó à seleção.

## Performance

A inicialização continua lazy e o `export` continua extraindo somente os IDs selecionados.

## Executar

```bash
python workflow_selection_lazy.py
```
