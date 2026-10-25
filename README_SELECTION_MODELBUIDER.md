# Selection Engine + ModelBuilder Exporter V1

Esta camada trabalha sobre o extrator scenario-aware V2.1.

## Selection Engine

Suporta:

- seleção por tipo;
- seleção por `Is Active`;
- IDs individuais;
- Labels individuais;
- filtros em atributos comuns;
- filtros em `Physical`;
- filtros em `UDX`;
- filtros em `Initial Settings`;
- inclusão automática dos nós necessários aos Pipes selecionados;
- `SelectionSet` serializável em JSON.

### Operadores de filtro

- `eq`
- `ne`
- `contains`
- `startswith`
- `endswith`
- `gt`
- `gte`
- `lt`
- `lte`
- `in` (para uso pela API Python)

## Exemplos

```text
select type Pipe
select active Pipe true
select id 12345 12346
select label P-100 P-101
filter Pipe Physical_PipeMaterial eq PVC
filter Pipe Physical_PipeDiameter gte 0.9842519685
filter Pipe UDX.SETOR_VRP eq SETOR_01
dependencies
summary
export
```

## ModelBuilder Exporter

Gera workbook limpo separado do workbook de diagnóstico.

Inclui:

- Selection Summary
- Pipes
- Junctions
- Reservoirs
- AirValves
- Hydrants
- Tanks
- TCVs
- FCVs
- PRVs
- PBVs
- CheckValves
- Pumps
- VSPB
- PipeVertices (referência)
- Import Notes

Nem toda aba será criada: apenas tipos efetivamente selecionados.

## Chave de rastreabilidade

`SourceElementID` é gerado como:

```text
WG_SRC_<DomainElementID>
```

A intenção é poder mapeá-lo para GIS-ID no WaterGEMS ou mantê-lo como UDX.

## Importante

A aba `PipeVertices` é de referência. A possibilidade de importar curvas intermediárias
diretamente depende do workflow/versão do ModelBuilder; a conectividade principal dos
Pipes é exportada por StartNodeLabel/StopNodeLabel.

## Executar

```bash
pip install -r requirements.txt
python workflow_selection.py
```
