# WaterGEMS ModelBuilder Tool V3.5.5

## Tabela: novos grupos de colunas

A janela `Colunas tabela` agora possui:

- Core
- Geometry
- ModelBuilder / Exportação
- Physical
- User Data Extensions
- Initial Settings

## Geometry

Para nós (Junction, Reservoir, Tank, válvulas, pumps etc.):

- Geometry.HasGeometry
- Geometry.SourceScenarioID
- Geometry.AlternativeID
- Geometry.X
- Geometry.Y

Para Pipe:

- Geometry.HasGeometry
- Geometry.SourceScenarioID
- Geometry.AlternativeID
- Geometry.VertexCount
- Geometry.StartNodeID
- Geometry.StartNodeLabel
- Geometry.StartNodeType
- Geometry.StartNodeResolution
- Geometry.StartX
- Geometry.StartY
- Geometry.StopNodeID
- Geometry.StopNodeLabel
- Geometry.StopNodeType
- Geometry.StopNodeResolution
- Geometry.StopX
- Geometry.StopY

As coordenadas Geometry vêm do armazenamento WaterGEMS e respeitam o seletor
SI/US da interface.

## ModelBuilder / Exportação

Mostra, de forma lazy, os mesmos campos canônicos configuráveis do exportador
WaterGEMS 2019, prefixados por `ModelBuilder.`.

Exemplo para Junction:

- ModelBuilder.SourceElementID
- ModelBuilder.SourceDomainElementID
- ModelBuilder.Label
- ModelBuilder.IsActive
- ModelBuilder.X_m
- ModelBuilder.Y_m
- ModelBuilder.Elevation_m
- ModelBuilder.SourceElementType

Exemplo para Pipe:

- ModelBuilder.StartNodeLabel
- ModelBuilder.StopNodeLabel
- ModelBuilder.StartNodeSourceID
- ModelBuilder.StopNodeSourceID
- ModelBuilder.StartNodeResolution
- ModelBuilder.StopNodeResolution
- ModelBuilder.Diameter_mm
- ModelBuilder.Material
- ModelBuilder.HazenWilliamsC
- ModelBuilder.ManningsN
- ModelBuilder.Length_m

Esses valores refletem o caminho atual do exportador. Portanto são úteis para
comparar `Geometry.X/Y` com `ModelBuilder.X_m/Y_m` e identificar se um problema
é apenas visual ou também afetaria o Excel.

## Caso Pipe 450559

Uma forma direta de diagnóstico agora é:

1. adicionar as duas dependências do Pipe;
2. abrir Junction;
3. ativar `Mostrar apenas selecionados`;
4. Colunas tabela -> Geometry;
5. marcar `Geometry.X`, `Geometry.Y`, `Geometry.HasGeometry`;
6. também marcar `ModelBuilder.X_m`, `ModelBuilder.Y_m`.

Se Geometry tiver coordenadas e ModelBuilder não, existe divergência entre o
resolvedor espacial e o extrator/exportador.
Se ambos estiverem vazios para uma Junction, o problema também pode afetar a
posição no arquivo de exportação.
