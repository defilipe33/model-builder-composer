# WaterGEMS ModelBuilder Tool V3.5.4

## Correção de herança de geometria

Problema identificado:

O `AlternativeResolver.resolve_row()` retorna a primeira linha encontrada na
cadeia de Alternatives.

Para propriedades em que a linha filha pode existir com um campo NULL, isso
não é suficiente. Em particular:

```text
Scenario filho / Geometry Alternative
    existe linha para o elemento
    HMIGeometry = NULL

Scenario pai / Geometry Alternative
    HMIGeometry = WKB válido
```

O mapa parava na linha filha e concluía incorretamente que não existia
geometria.

## Nova lógica espacial

`SpatialRepository.geometry_with_source()` percorre:

```text
scenario selecionado
-> parent
-> parent
-> root
```

e:

- ignora Alternative sem linha;
- continua quando HMIGeometry é NULL;
- continua quando o WKB é inválido;
- usa a primeira HMIGeometry válida encontrada.

Isso vale para:
- Pipe;
- Junction;
- Reservoir;
- Tank;
- válvulas;
- pumps;
- demais tipos suportados.

## Diagnóstico

`Mapa > Diagnosticar seleção no mapa` mostra, para seleções pequenas, cada
Alternative consultada e o motivo:

- sem linha;
- linha encontrada, HMIGeometry NULL;
- WKB inválido;
- WKB válido.

Caso de teste principal:
`Pipe 450559`.
