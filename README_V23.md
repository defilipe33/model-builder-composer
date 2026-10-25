# WaterGEMS Lazy Selection + ModelBuilder Exporter V2.3

## Correção crítica: elementos deletados

O SQLite do WaterGEMS pode manter registros de elementos excluídos nas tabelas raiz.

Exemplo observado:

```text
IdahoPipe.DomainElementID = 109526
HMIDomainElement.IsDeleted = 1
HMIModelingElement.IsDeleted = 1
```

Mesmo deletado, o elemento ainda pode possuir:

- linha em `IdahoPipe`;
- Physical Data;
- Geometry;
- Topology residual;
- Change Tracking;
- GIS-ID.

Esses registros são tombstones internos e NÃO devem ser tratados como elementos
existentes no modelo.

## Nova regra

Todas as operações normais usam somente:

```text
HMIDomainElement.IsDeleted = 0
```

com fallback para `HMIModelingElement.IsDeleted = 0` se necessário.

Isso vale para:

- `types`
- `preview`
- `select type`
- `select id`
- `select label`
- filtros
- `dependencies`
- `extract-all`
- `export`
- Network Topology Resolver

O `export` valida novamente o status, inclusive para SelectionSets antigos.

## Relação com Active Topology

São conceitos diferentes:

```text
IsDeleted = 1
→ elemento foi removido do modelo
→ não exportar em nenhum cenário

IsDeleted = 0 + Is Active = False
→ elemento existe no modelo
→ apenas está inativo no cenário
→ exportar com IsActive=False
```

## Descoberta no diagnóstico

Na amostra Modelo_Ana:

```text
71 Pipes amostrados
64 deletados
7 não deletados
```

Nos 7 não deletados:

- 0 Start Nodes ausentes
- 0 Stop Nodes ausentes
- 0 geometrias com comprimento zero

Os casos problemáticos estavam concentrados nos tombstones deletados.

## Executar

```bash
python workflow_selection_lazy.py
```
