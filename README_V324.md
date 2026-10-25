# WaterGEMS ModelBuilder Tool V3.2.4

Correções:

- "Selecionar resultados do filtro" renomeado para "Marcar resultados do filtro".
- Comparações `=` e `!=` agora usam comparação numérica com tolerância quando
  ambos os valores são numéricos.
- Isso evita falhas causadas por conversões SI -> pés e representação binária
  de ponto flutuante.

Exemplo válido em SI:

```text
[Physical.Physical_PipeDiameter] = 252.0
```

Também é aceito:

```text
[Physical.Physical_PipeDiameter] = '252.0'
```

Se a amostra da interface mostrar 252.0 mm, ambas as expressões devem localizar
os mesmos elementos.
