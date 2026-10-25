# WaterGEMS Lazy Selection + ModelBuilder Exporter V2.5

## Dynamic columns by element type

At startup the program inspects the actual SQLite schema and discovers fields for:

- Core
- Physical
- UDX
- Initial Settings

No UDX field is hardcoded.

For a model with custom fields, for example:

```text
SETOR_VRP
Concepcao
TAG
Faseamento
NM_Adutora
```

they appear automatically when the corresponding table/column exists.

## Commands

```text
columns available Pipe
```

Example:

```text
CORE
  SourceElementID
  Label
  Diameter_mm
  ...

PHYSICAL
  Physical.Physical_PipeDiameter
  Physical.Setor
  Physical.TAG
  ...

UDX
  UDX.SETOR_VRP
  UDX.Concepcao

INITIAL
  Initial....
```

Select all:

```text
columns all Pipe
```

Only UDX:

```text
columns group Pipe udx
```

Add UDX to current Core selection:

```text
columns add Pipe UDX.SETOR_VRP UDX.Concepcao
```

Set exact columns:

```text
columns set Pipe SourceElementID Label UDX.SETOR_VRP Physical.TAG
```

Reset to default Core columns:

```text
columns reset Pipe
```

## Export

Selected dynamic columns are written as normal Excel columns, making them available for
manual mapping in WaterGEMS 2019 ModelBuilder.

The default remains concise (Core only) to avoid creating excessively wide workbooks.
