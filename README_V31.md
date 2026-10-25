# WaterGEMS ModelBuilder Tool V3.1 — Filtros e seleção avançada

## Novidades

### Filtros dinâmicos

A GUI permite filtrar por:

- Core
- Physical
- User Data Extensions
- Initial Settings

Operadores:

- =
- !=
- contém
- começa com
- termina com
- >
- >=
- <
- <=

Exemplos de campos:

```text
Core.ID
Core.Label
Core.IsActive
Physical.Physical_PipeMaterial
Physical.TAG
UDX.SETOR_VRP
Initial....
```

### Paginação + filtro

A tabela continua lazy/paginada.

Exemplo:

```text
200 itens/página
3.482 resultados filtrados
```

### Seleção em massa

- Selecionar página
- Desmarcar página
- Selecionar resultados do filtro
- Desmarcar resultados do filtro

### Seleção estilo desktop

A tabela usa seleção estendida nativa do Qt:

```text
Clique
Ctrl + clique
Shift + clique
Ctrl + A
Ctrl + Shift + A
Espaço
```

Comportamento:

```text
Shift + clique
→ seleciona visualmente intervalo de linhas

Espaço
→ marca/desmarca os checkboxes das linhas visualmente selecionadas
```

A seleção visual da tabela é diferente do `SelectionSet`.

### Colunas da tabela

Nova janela independente de colunas para visualização.

Ela não interfere nas colunas de exportação do ModelBuilder.

Assim o usuário pode exibir:

```text
Core.Label
Physical.TAG
UDX.SETOR_VRP
```

na tabela para ajudar na seleção, mas exportar outro conjunto de campos.

## Arquitetura

Mantida:

- startup lazy;
- paginação;
- SelectionSet por tipo + ID;
- extração seletiva;
- tombstone filtering;
- NetworkTopologyResolver;
- colunas dinâmicas para export;
- CLI separado.

## Executar

```bash
python -m pip install -r requirements.txt
python app_gui.py
```

## Nota de performance

Alguns filtros dinâmicos ainda resolvem os candidatos no Python, principalmente
Initial Settings. Isso é suficiente para validar a UX da V3.1.

Uma versão posterior pode otimizar filtros pesados com SQL/batches sem alterar a GUI.
