# WaterGEMS ModelBuilder Tool V3.5.3

## Correções

### Zoom Selection
O botão `Zoom Selection` dentro do painel do mapa e a ação
`Mapa > Zoom Selection` agora usam exatamente o mesmo método robusto da
MainWindow.

Antes, o botão interno ainda chamava diretamente o widget e podia falhar
silenciosamente quando a geometria selecionada ainda não estava na cena.

### Pipe geometry fallback
Para Pipe selecionado:

1. tenta a geometria WKB scenario-aware normal;
2. se não existir/não decodificar, resolve StartNode e StopNode;
3. busca as coordenadas scenario-aware dos dois nós;
4. desenha um segmento reto temporário entre eles.

Esse fallback é apenas visual e não altera exportação, banco ou topologia.

### Diagnóstico
Novo menu:

`Mapa > Diagnosticar seleção no mapa`

Mostra:
- SelectionSet;
- geometrias resolvidas;
- selecionados já presentes na cena;
- quantidade usando fallback;
- IDs sem geometria.

O caso de teste informado foi `Pipe 450559`.
