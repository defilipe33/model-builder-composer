# WaterGEMS ModelBuilder Tool V3.0 — PySide6 GUI

A V3.0 adiciona uma interface gráfica sobre a arquitetura lazy existente.

## Instalação

```bash
pip install -r requirements.txt
```

## Executar GUI

```bash
python app_gui.py
```

O CLI continua disponível:

```bash
python workflow_selection_lazy.py
```

## Fluxo da GUI

1. Abrir `.wtg.sqlite`.
2. Escolher cenário.
3. Carregar cenário.
4. Escolher tipo de elemento.
5. Navegar pela tabela paginada.
6. Selecionar por checkbox ou por lista de IDs.
7. Adicionar dependências dos Pipes.
8. Configurar colunas Core / Physical / UDX / Initial.
9. Exportar para `.xlsx`.

## Lazy loading

A tabela não carrega o banco inteiro.

Ela usa páginas:

```text
offset + limit
```

e mantém no `SelectionSet` apenas:

```text
tipo + DomainElementID
```

A extração completa ocorre somente ao exportar e somente para os IDs selecionados.

## Dependências

`Adicionar dependências dos Pipes` atua somente sobre Pipes selecionados.

Elementos pontuais como Junction, PRV, TCV, Tank e Pump não expandem
automaticamente a rede.

## Colunas dinâmicas

A janela `Colunas...` descobre os campos existentes no modelo e os organiza em:

- Core
- Physical
- User Data Extensions
- Initial Settings

O conjunto padrão é Core. O usuário escolhe explicitamente os campos adicionais.

## Escopo desta V3.0

Incluído:

- arquivo/cenário;
- tipos;
- tabela paginada;
- checkboxes;
- seleção por IDs;
- resumo;
- dependências;
- configuração de colunas;
- export.

Ainda não incluído:

- mapa;
- filtros avançados pela GUI;
- expansão upstream/downstream;
- seleção espacial;
- execução em worker thread.

Esses pontos ficam para as próximas versões.
