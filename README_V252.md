# WaterGEMS Lazy Selection + ModelBuilder Exporter V2.5.2

## Correção

Restaura corretamente `LazySelectionEngine.select_ids()` e mantém a descoberta
dinâmica de colunas da V2.5.

Exemplos válidos:

```text
select id pipe 450577 450570
select id junction 123 456
select id prv 1001 1002
select id tcv 2001 2002
select id "standard pump" 3001
```

## Dependências

- `Pipe`: requer os elementos de extremidade para conectividade no ModelBuilder.
- `Junction`, `Reservoir`, `Tank`, `PRV`, `TCV`, `FCV`, `PBV`, `Check Valve`,
  `Pump`, `Air Valve`, `Hydrant` etc.: não recebem dependências automáticas.
- `dependencies` atua somente sobre os Pipes já selecionados.
- Selecionar um elemento pontual não puxa automaticamente os links conectados.

Isso evita expandir a seleção de forma inesperada.
