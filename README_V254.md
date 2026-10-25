# WaterGEMS Lazy Selection + ModelBuilder Exporter V2.5.4

## Correção

Corrige recursão infinita em `append_dynamic_fields()`.

Na V2.5.x a função terminava com:

```python
return append_dynamic_fields(row, element)
```

o que causava:

```text
maximum recursion depth exceeded
```

Agora termina corretamente com:

```python
return row
```

Mantém:
- colunas dinâmicas Core / Physical / UDX / Initial;
- export seletivo;
- tombstone filtering;
- NetworkTopologyResolver;
- seleção por IDs;
- robustez de entrada.
