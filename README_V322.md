# WaterGEMS ModelBuilder Tool V3.2.2

## Interface responsiva

- janela inicial = ~78% da área útil do monitor;
- limite máximo inicial = 1600 x 900;
- sempre centralizada;
- usuário pode maximizar normalmente;
- nenhum redimensionamento interno chama `resize()` novamente.

## Splitters

O divisor principal e o divisor do filtro agora:

- usam `QSplitter`;
- têm handle maior;
- não colapsam panes para zero;
- não usam largura máxima rígida;
- mantêm os painéis flexíveis;
- não devem alterar o estado maximizado da janela.

## Botões

Os seis comandos de seleção da tabela são distribuídos em duas linhas.

Os dez operadores do editor são distribuídos em duas linhas de cinco botões.

## Amostras

A antiga lista suspensa foi substituída por uma janela própria:

- lista grande;
- scroll vertical/horizontal;
- duplo clique confirma;
- clique simples + botão Confirmar;
- Cancelar.

## Cenários

A resolução de nomes agora tenta:

1. `HMIScenario.ScenarioID -> HMIModelingElement.ElementID -> Label/SmartLabel`;
2. procura conservadoramente uma tabela auxiliar com ScenarioID/SupportElementID
   e coluna Name/Label;
3. fallback: `Scenario <ID>`.

Nos bancos diagnósticos disponíveis, o cenário raiz ID=1 resolve para
`BASE_COMPLETO`, enquanto os demais IDs não estão presentes diretamente em
`HMIModelingElement`. O banco completo do usuário poderá conter esses support
elements, como aconteceu com Selection Sets.
