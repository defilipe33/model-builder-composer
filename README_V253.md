# WaterGEMS Lazy Selection + ModelBuilder Exporter V2.5.3

Correção de integração no `ModelRepository`.

O erro:

```text
'ModelRepository' object has no attribute 'is_deleted_id'
```

era causado por indentação incorreta: `is_deleted_id()` ficou fora da classe e
`is_live_id()` ficou aninhado indevidamente.

Nesta versão foram validados como métodos reais de `ModelRepository`:

- `is_deleted_id`
- `is_live_id`
- `has_id`

Mantém todas as funcionalidades da V2.5.2, inclusive colunas dinâmicas.
