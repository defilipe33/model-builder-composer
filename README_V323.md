# WaterGEMS ModelBuilder Tool V3.2.3

## Layout
- janela inicial permanece proporcional ao monitor e centralizada;
- tamanho mínimo da aplicação aumentado para proteger a interface;
- painel "Tipos e filtros" ganhou maior largura mínima/proporção;
- painel SelectionSet ganhou menor proporção inicial;
- editor de expressão tem largura mínima de segurança;
- operadores continuam em duas linhas e não devem se sobrepor.

## Botões da tabela
Pares verticais:
- Marcar seleção visual / Desmarcar seleção visual
- Marcar página / Desmarcar página
- Selecionar resultados do filtro / Desmarcar resultados do filtro

## Toolbar
- Abrir
- Selection Sets
- Colunas tabela
- Colunas exportação
- Unidades: SI / Americano
- Exportar
- Mapa (reservado para versão futura)

## Unidades de exibição
Padrão: SI.

Campos dimensionais WaterGEMS conhecidos:
- diâmetros: mm no SI / in no US;
- elevações, níveis e comprimentos conhecidos: m no SI / ft no US.

A conversão é aplicada:
- tabela;
- amostras;
- valores numéricos usados em filtros.

Campos auxiliares desconhecidos não são convertidos por heurística para evitar
interpretar uma coluna incorretamente.

## Indicador de atividade
A barra de status mostra uma barra indeterminada durante operações cujo progresso
exato ainda não é mensurável, como:
- abrir banco;
- carregar cenário;
- aplicar filtro;
- ler amostras;
- resolver dependências;
- carregar Selection Set;
- exportar.

## Duplicatas
SelectionSet interno usa `set[int]` por tipo. Portanto o mesmo `tipo + ID` nunca
é armazenado duas vezes.
