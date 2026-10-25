# WaterGEMS ModelBuilder Tool V3.6
## Expansão topológica com critérios de parada

Novo comando:

```text
Topologia
→ Expandir até elemento de parada...
```

### Configurações

- Direção:
  - Conectados
  - Upstream topológico
  - Downstream topológico

- Máximo de níveis

- Tipos de parada:
  - qualquer tipo suportado
  - atalhos para Reservoir + Tank
  - válvulas
  - Pumps

- Incluir ou não o elemento de parada no SelectionSet

- Opção:
  `Encerrar toda a expansão ao encontrar o primeiro elemento de parada`

Por padrão, essa opção fica desativada. Assim, cada ramificação para quando
encontra o critério, mas as outras ramificações continuam sendo analisadas.

### Semântica

A direção continua exclusivamente topológica:

```text
StartNode -> Pipe -> StopNode
```

Não são usados resultados hidráulicos.

### Undo

Toda a expansão é um único passo no histórico de seleção.

### Limites de segurança

- 50.000 novos elementos
- 100.000 elementos visitados
- máximo de níveis definido pelo usuário

### Relatório

Ao final, a aplicação informa:

- novos elementos adicionados;
- quantidade por tipo;
- quantidade visitada;
- elementos de parada encontrados;
- paradas por tipo;
- se algum limite de segurança foi atingido.
