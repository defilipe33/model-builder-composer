# WaterGEMS Lazy Selection + ModelBuilder Exporter V2.1

Foco desta versão:

1. robustez de entrada;
2. extração realmente seletiva.

## Robustez

Erros do usuário não encerram o programa.

Exemplos tratados:

- caminho inexistente;
- arquivo sem extensão `.sqlite`;
- comando desconhecido;
- argumentos faltantes;
- IDs não numéricos;
- preview com limite inválido;
- tipo com maiúsculas/minúsculas diferentes;
- saída sem `.xlsx`;
- diretório de saída inexistente;
- aspas malformadas.

Tipos são case-insensitive:

```text
preview pipe 20
preview PIPE 20
preview Pipe 20
```

são equivalentes.

## Export seletivo

O comando `export` não executa mais `extract_all()`.

Ele extrai somente:

```text
tipo + IDs presentes no SelectionSet
```

Exemplo:

```text
10 Pipes + 9 nós
```

gera consultas e objetos apenas para esses elementos.

## Executar

```bash
python workflow_selection_lazy.py
```
