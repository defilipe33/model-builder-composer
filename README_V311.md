# WaterGEMS ModelBuilder Tool V3.1.1

## Correções

### Tabela vazia / filtros sem funcionar

Na V3.1 alguns métodos do `AppBackend` ficaram fora da classe por um erro de
indentação:

- `available_table_fields`
- `filtered_ids`
- `table_page`
- `select_many`
- `deselect_many`
- `export`

A V3.1.1 reconstrói o backend corretamente.

## Troca de cenário

Se já existe um cenário carregado e o usuário escolher outro:

```text
Mensagem de confirmação
→ se cancelar: nada muda
→ se confirmar:
   - limpa SelectionSet
   - limpa filtros
   - limpa página/tabela
   - limpa configurações temporárias da tabela
   - mantém o SQLite aberto
   - carrega o novo cenário
```

## Troca de SQLite

Se já existe arquivo aberto:

```text
Mensagem de confirmação
→ se cancelar: nada muda
→ se confirmar:
   - fecha banco atual
   - limpa cenário
   - limpa seleção
   - limpa filtros
   - limpa tabela
   - limpa configurações
   - abre o novo SQLite
```

## Selection Sets nativos do WaterGEMS

Foi confirmado nos bancos diagnósticos:

```text
HMISelectionSet
  SelectionSetID
  SelectionSetType
  SelectionSetCount
  SelectionSetElementIDs (BLOB)
```

O BLOB é uma sequência little-endian de inteiros uint32 e seu número de itens
coincide com `SelectionSetCount`.

A GUI agora possui:

```text
Selection Sets do WaterGEMS...
```

A lista inicial carrega apenas metadados.

Os membros só são decodificados quando o usuário escolhe:

- `Adicionar à seleção atual`
- `Substituir seleção atual`

A classificação dos membros por Pipe/Junction/PRV/etc. também ocorre somente
nessa hora.

### Nome dos Selection Sets

Os bancos diagnósticos preservaram `HMISelectionSet`, mas não a estrutura de
metadados que contém o nome amigável.

A V3.1.1 tenta descobrir dinamicamente uma tabela que relacione
`SelectionSetID`/`SupportElementID` a `Name`/`Label`.

Se não encontrar, mostra de forma segura:

```text
Selection Set <ID>
```

em vez de inventar um nome.

Um diagnóstico do SQLite completo poderá confirmar a tabela exata de nomes para
eliminarmos esse fallback futuramente.
