# WaterGEMS Lazy Selection + ModelBuilder Exporter V2.4

## 1. Relatório seguro em `select id`

Exemplo:

```text
select id Pipe 100 101 999 109526
```

Resposta:

```text
Solicitados: 4
Selecionados agora: 2
Já selecionados: 0
Não encontrados: 1
Deletados: 1

Não encontrados:
  999

Deletados:
  109526
```

Se houver texto:

```text
select id Pipe 100 abc 101 teste
```

Resposta:

```text
IDs inválidos:
  abc
  teste

Os demais IDs válidos não foram processados.
```

Nenhuma seleção parcial é feita nesse caso.

## 2. Colunas configuráveis por tipo

O exporter do ModelBuilder agora aceita configuração de colunas por tipo de elemento.

### Ver colunas atuais

```text
columns Pipe
```

### Ver colunas padrão disponíveis

```text
columns available Pipe
```

### Definir colunas

```text
columns set Pipe SourceElementID Label StartNodeLabel StopNodeLabel Diameter_mm Material
```

### Restaurar padrão

```text
columns reset Pipe
```

Tipos com espaço podem ser passados entre aspas quando necessário:

```text
columns "Air Valve"
```

A configuração é mantida em memória durante a sessão.

## Objetivo

Permitir preparar planilhas diferentes para o ModelBuilder dependendo do mapeamento
que o usuário pretende fazer no WaterGEMS 2019.
