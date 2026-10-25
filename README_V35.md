# WaterGEMS ModelBuilder Tool V3.5 — Topology Expansion

## Toolbar: Topologia

- Expandir 1 nível
- Expandir N níveis...
- Upstream — 1 nível
- Upstream — N níveis...
- Downstream — 1 nível
- Downstream — N níveis...

## Semântica do grafo

```text
StartNode -> Pipe -> StopNode
```

Um passo topológico é:

```text
Pipe -> nó
ou
nó -> Pipe
```

Por isso:

```text
Pipe selecionado
Expandir 1 nível
→ adiciona StartNode + StopNode

Expandir 2 níveis
→ pode chegar aos Pipes conectados a esses nós
```

## Direção

Upstream:
- Pipe -> StartNode
- Node -> Pipes que terminam no Node

Downstream:
- Pipe -> StopNode
- Node -> Pipes que começam no Node

Conectados:
- ambos os sentidos

## Cenário

A topologia é resolvida pelo cenário ativo, usando a cadeia de Alternatives já
implementada. Registros antigos de alternativas pai não são usados como links
válidos quando existe override no cenário filho.

## Undo

Cada expansão é registrada como uma única alteração do SelectionSet e pode ser
desfeita pela função global Undo.

## Limites

- 50.000 novos elementos por expansão
- 100.000 elementos visitados

Se um limite for alcançado, a expansão para e informa o usuário.

## Mapa

Se o mapa estiver aberto, ele é atualizado após a expansão para que os novos
elementos selecionados apareçam imediatamente em vermelho.

## Atualização regional

Permanece experimental/standby. A V3.5 não depende dela.
