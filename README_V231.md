# WaterGEMS Lazy Selection + ModelBuilder Exporter V2.3.1

Correção de manutenção da V2.3.

## Bug corrigido

Na V2.3, um erro de indentação colocou `_is_live()` fora da classe
`SelectiveExtractionService`, fazendo com que `extract_selected()` deixasse de
ser um método da classe.

O sintoma era:

```text
'SelectiveExtractionService' object has no attribute 'extract_selected'
```

A V2.3.1 mantém a mesma lógica funcional da V2.3:

- elementos deletados (`IsDeleted = 1`) são excluídos;
- elementos existentes com `IsActive = False` continuam exportáveis;
- startup lazy;
- export seletivo;
- NetworkTopologyResolver;
- validação robusta de entrada.

## Contagem em `types`

Exemplo:

```text
Pipe: 254599  (deleted tombstones excluded: 18432)
```

significa:

- 254.599 Pipes vivos/utilizáveis;
- 18.432 tombstones deletados, não incluídos na contagem principal.

Total de registros raiz relacionados: 273.031.
