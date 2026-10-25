# WaterGEMS ModelBuilder Tool V3.4.2

## Correção da seleção espacial
Corrigido:

```text
ModelRepository.is_live_id() takes 2 positional arguments but 3 were given
```

`is_live_id` recebe apenas `element_id`. A seleção espacial agora valida:

```text
has_id(element_type, element_id)
AND is_live_id(element_id)
```

## SelectionSet como fonte de verdade

O SelectionSet é o estado real da aplicação.

Após qualquer mudança de seleção, os checkboxes visíveis da tabela são
ressincronizados com ele. Portanto não deve mais existir situação em que o
resumo diz `Pipe: 1` mas várias caixas permanecem visualmente marcadas.

## Undo / Redo geral

Agora ficam na toolbar principal, não no menu Mapa:

- Desfazer (`Ctrl+Z`)
- Refazer (`Ctrl+Y`)

Até 30 estados são mantidos.

Uma nova alteração após Undo limpa corretamente o ramo de Redo.

## Mostrar apenas selecionados na tabela

Novo checkbox:

```text
Mostrar apenas selecionados
```

Quando ativo:
- mantém o tipo/filtro atual;
- intersecta os resultados com o SelectionSet;
- em `Todos os elementos`, mostra os pares tipo+ID atualmente selecionados;
- ao desmarcar um item, ele desaparece da tabela na próxima sincronização.
