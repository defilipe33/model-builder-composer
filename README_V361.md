# WaterGEMS ModelBuilder Tool V3.6.1 — Simbologia do mapa

## Novo menu

```text
Mapa
→ Simbologia...
→ Restaurar simbologia padrão
```

## Modos

### Padrão por tipo

Cada família pontual recebe um símbolo visual.

Padrões iniciais:

- Junction: círculo
- Reservoir: quadrado
- Tank / Conventional Tank: triângulo
- Hydrant: estrela
- válvulas: losango
- Pumps: cruz

### Todos os elementos pontuais iguais

Permite escolher um único símbolo para todos os elementos nodais.

## Válvulas

Há uma opção:

```text
Usar um símbolo comum para válvulas
```

incluindo:
- TCV
- FCV
- PRV
- PBV
- Check Valve
- Air Valve

O símbolo comum também é configurável.

## Sobrescrições por tipo

Qualquer tipo pode ter uma configuração própria, que tem prioridade sobre as
regras gerais.

Exemplo:

```text
Válvulas gerais = losango
PRV = estrela
Check Valve = X
```

## Símbolos disponíveis

- Círculo
- Quadrado
- Losango
- Triângulo
- Cruz +
- X
- Estrela

Todos os símbolos pontuais usam tamanho fixo na tela para continuar legíveis
durante zoom.

## Seleção

A simbologia representa o tipo; a cor representa seleção:

- não selecionado: claro
- selecionado: vermelho

Assim um Reservoir continua quadrado quando é selecionado, apenas muda para
vermelho.

## Legenda

Uma legenda fica sobreposta no canto inferior direito do mapa e acompanha a
simbologia atual.

Ela também documenta:
- Pipe normal;
- Pipe com comprimento aproximadamente zero;
- nós coincidentes.

## Restaurar padrão

`Mapa → Restaurar simbologia padrão` retorna imediatamente às regras iniciais.
