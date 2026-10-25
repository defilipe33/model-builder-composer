from pathlib import Path
import shlex

from database.connection import WaterGemsDatabase
from database.schema import SchemaInspector
from readers.common import CommonReader
from readers.scenario_aware import ScenarioAwareReaders
from scenario.scenario_reader import ScenarioReader
from scenario.resolver import AlternativeResolver

from repository.model_repository import ModelRepository
from repository.query_repository import QueryRepository
from repository.selective_extraction import SelectiveExtractionService
from repository.network_topology import NetworkTopologyResolver
from selection.lazy_engine import LazySelectionEngine
from modelbuilder.exporter import export_modelbuilder
from modelbuilder.column_config import ColumnConfig
from repository.dynamic_fields import DynamicFieldDiscovery


VALID_INPUT_SUFFIXES = (".sqlite",)
VALID_OUTPUT_SUFFIX = ".xlsx"


def ask_sqlite_path():
    while True:
        raw = input("\nCaminho do .wtg.sqlite:\n> ").strip().strip('"').strip("'")
        if not raw:
            print("Informe um caminho.")
            continue

        path = Path(raw)

        if not path.exists():
            print("Arquivo não encontrado.")
            continue
        if not path.is_file():
            print("O caminho informado não é um arquivo.")
            continue
        if path.suffix.lower() not in VALID_INPUT_SUFFIXES:
            print("O arquivo deve ter extensão .sqlite.")
            continue

        return path


def choose_scenario(reader):
    scenarios = reader.tree_order()
    active_id = reader.active_scenario_id()

    if not scenarios:
        raise RuntimeError("Nenhum cenário encontrado.")

    print("\nCENÁRIOS")
    for i, s in enumerate(scenarios, start=1):
        indent = "    " * s.depth
        marker = " [ATIVO]" if s.is_active else ""
        print(f"[{i:>2}] {indent}{s.display_name} (ID {s.id}){marker}")

    while True:
        raw = input("\nEscolha [ENTER = ativo]: ").strip()

        if not raw:
            if active_id is not None:
                return active_id
            print("Não foi possível identificar cenário ativo. Escolha um número.")
            continue

        try:
            idx = int(raw)
        except ValueError:
            print("Digite o número correspondente ao cenário.")
            continue

        if 1 <= idx <= len(scenarios):
            return scenarios[idx - 1].id

        print("Opção inválida.")


def open_repository(sqlite_path):
    db = WaterGemsDatabase(sqlite_path)
    schema = SchemaInspector(db)
    common = CommonReader(db, schema)

    scenario_reader = ScenarioReader(db, schema)
    selected_id = choose_scenario(scenario_reader)

    resolver = AlternativeResolver(db, schema)
    context = resolver.build_context(selected_id)
    readers = ScenarioAwareReaders(resolver)

    model_repo = ModelRepository(db, schema, common, resolver, context)
    query_repo = QueryRepository(model_repo)
    topology_resolver = NetworkTopologyResolver(
        db, schema, common, resolver, context
    )
    extraction = SelectiveExtractionService(
        db, schema, common, readers, context, topology_resolver
    )

    return db, model_repo, query_repo, extraction, context, topology_resolver


def parse_value(raw):
    text = raw.strip().strip('"').strip("'")
    low = text.lower()

    if low == "true":
        return True
    if low == "false":
        return False
    if low in {"none", "null"}:
        return None

    try:
        return int(text)
    except ValueError:
        pass

    try:
        return float(text)
    except ValueError:
        return text


def parse_bool(raw):
    value = parse_value(raw)
    if isinstance(value, bool):
        return value
    raise ValueError('Use "true" ou "false".')


def validate_output_path(raw, default):
    if not raw:
        return default

    path = Path(raw.strip().strip('"').strip("'"))

    if path.exists() and path.is_dir():
        return path / default.name

    if path.suffix == "":
        parent = path.parent
        if parent != Path(".") and not parent.exists():
            raise ValueError("O diretório informado não existe.")
        return path.with_suffix(VALID_OUTPUT_SUFFIX)

    if path.suffix.lower() != VALID_OUTPUT_SUFFIX:
        raise ValueError("O arquivo de saída deve ter extensão .xlsx.")

    if not path.parent.exists():
        raise ValueError("O diretório de saída não existe.")

    return path


def print_help():
    print("""
COMANDOS

  types
      Lista tipos e contagens.

  preview Pipe 20
      Mostra os primeiros 20 elementos.
      O nome do tipo NÃO diferencia maiúsculas/minúsculas.

  select type Pipe
      Seleciona todos os IDs do tipo.

  select active Pipe true
      Seleciona pelo Active Topology.

  select id Pipe 123 456
      Seleciona IDs individuais.

  select label Pipe "P-100" "P-101"
      Seleciona Labels individuais.

  filter Pipe physical Physical_PipeMaterial eq PVC
  filter Pipe udx SETOR_VRP eq "SETOR 01"
      Filtros sob demanda.

  dependencies
      Inclui os elementos de extremidade necessários aos Pipes selecionados.

  summary
      Resume a seleção.

  clear
      Limpa a seleção.

  columns <tipo>
      Mostra as colunas atualmente configuradas para o tipo.

  columns available <tipo>
      Mostra todas as colunas disponíveis, agrupadas em Core/Physical/UDX/Initial.

  columns set <tipo> <coluna1> <coluna2> ...
      Define exatamente as colunas exportadas.

  columns add <tipo> <coluna1> <coluna2> ...
      Adiciona colunas às já selecionadas.

  columns group <tipo> <core|physical|udx|initial>
      Seleciona somente um grupo inteiro.

  columns all <tipo>
      Seleciona todas as colunas disponíveis.

  columns reset <tipo>
      Volta ao conjunto Core padrão.

  export
      Extrai SOMENTE os IDs selecionados e gera Excel ModelBuilder.

  extract-all
      Seleciona explicitamente todos os elementos de todos os tipos.

  help
  quit

Erros de digitação/argumentos não encerram o programa.
""")


def run_command(raw, engine, selection, source, extraction, context, column_config):
    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        print(f"Erro de sintaxe: {exc}")
        return False

    if not parts:
        return False

    cmd = parts[0].casefold()

    if cmd == "quit":
        return True

    if cmd == "help":
        print_help()
        return False

    if cmd == "types":
        for t, count in engine.available_types():
            deleted = engine.model.count_deleted_type(t)
            suffix = f"  (deleted tombstones excluded: {deleted})" if deleted else ""
            print(f"{t}: {count}{suffix}")
        return False

    if cmd == "clear":
        selection.clear()
        print("Seleção limpa.")
        return False

    if cmd == "summary":
        print(f"Total selecionado: {selection.count()}")
        for k, v in engine.summary(selection).items():
            print(f"  {k}: {v}")
        return False

    if cmd == "dependencies":
        added = engine.include_pipe_dependencies(selection)
        print(f"Dependências adicionadas: {added}")
        return False

    if cmd == "preview":
        if len(parts) not in (2, 3):
            raise ValueError("Uso: preview <tipo> [limite]")

        element_type = parts[1]
        limit = 50

        if len(parts) == 3:
            try:
                limit = int(parts[2])
            except ValueError:
                raise ValueError("O limite do preview deve ser um número inteiro.")

        rows = engine.preview(element_type, limit=limit)
        if not rows:
            print("Nenhum elemento encontrado.")
            return False

        for row in rows:
            print(f"{row['id']}\t{row['label']}")
        return False

    if cmd == "select":
        if len(parts) < 3:
            raise ValueError("Comando select incompleto.")

        mode = parts[1].casefold()

        if mode == "type":
            if len(parts) < 3:
                raise ValueError("Uso: select type <tipo>")
            element_type = " ".join(parts[2:])
            n = engine.select_type(selection, element_type)
            print(f"Selecionados: {n}")
            return False

        if mode == "active":
            if len(parts) != 4:
                raise ValueError("Uso: select active <tipo> <true|false>")
            element_type = parts[2]
            expected = parse_bool(parts[3])
            n = engine.select_active(selection, element_type, expected)
            print(f"Selecionados: {n}")
            return False

        if mode == "id":
            if len(parts) < 4:
                raise ValueError("Uso: select id <tipo> <id1> [id2...]")

            element_type = parts[2]
            raw_ids = parts[3:]

            invalid = [x for x in raw_ids if not x.lstrip("-").isdigit()]
            if invalid:
                print("IDs inválidos:")
                for value in invalid:
                    print(f"  {value}")
                print()
                print("Os demais IDs válidos não foram processados.")
                return False

            ids = [int(x) for x in raw_ids]
            report = engine.select_ids(selection, element_type, ids)

            print(f"Solicitados: {report['requested']}")
            print(f"Selecionados agora: {report['selected_now']}")
            print(f"Já selecionados: {report['already_selected']}")
            print(f"Não encontrados: {len(report['not_found'])}")
            print(f"Deletados: {len(report['deleted'])}")

            if report["not_found"]:
                print()
                print("Não encontrados:")
                for element_id in report["not_found"]:
                    print(f"  {element_id}")

            if report["deleted"]:
                print()
                print("Deletados:")
                for element_id in report["deleted"]:
                    print(f"  {element_id}")

            return False

        if mode == "label":
            if len(parts) < 4:
                raise ValueError("Uso: select label <tipo> <label1> [label2...]")
            element_type = parts[2]
            labels = parts[3:]
            n = engine.select_labels(selection, element_type, labels)
            print(f"Selecionados: {n}")
            return False

        raise ValueError(f'Modo select "{parts[1]}" não reconhecido.')

    if cmd == "filter":
        if len(parts) < 6:
            raise ValueError(
                "Uso: filter <tipo> <physical|udx> <campo> <operador> <valor>"
            )

        element_type = parts[1]
        namespace = parts[2].casefold()
        if namespace not in {"physical", "udx"}:
            raise ValueError('Namespace deve ser "physical" ou "udx".')

        field = parts[3]
        op = parts[4].casefold()
        value = parse_value(" ".join(parts[5:]))

        n = engine.select_filter(
            selection, element_type, namespace, field, op, value
        )
        print(f"Selecionados: {n}")
        return False

    if cmd == "columns":
        if len(parts) < 2:
            raise ValueError(
                "Uso: columns <tipo> | columns available <tipo> | "
                "columns set/add/group/all/reset ..."
            )

        sub = parts[1].casefold()

        if sub == "available":
            if len(parts) < 3:
                raise ValueError("Uso: columns available <tipo>")
            element_type = engine.normalize_type(" ".join(parts[2:]))
            groups = column_config.groups(element_type)
            print(f"Colunas disponíveis para {element_type}:")
            for group in ("core", "physical", "udx", "initial"):
                print()
                print(group.upper())
                for c in groups.get(group, []):
                    print(f"  {c}")
            return False

        if sub == "reset":
            if len(parts) < 3:
                raise ValueError("Uso: columns reset <tipo>")
            element_type = engine.normalize_type(" ".join(parts[2:]))
            column_config.reset(element_type)
            print(f"Colunas Core restauradas para {element_type}.")
            return False

        if sub == "all":
            if len(parts) < 3:
                raise ValueError("Uso: columns all <tipo>")
            element_type = engine.normalize_type(" ".join(parts[2:]))
            column_config.select_all(element_type)
            print(f"Todas as colunas selecionadas para {element_type}.")
            return False

        if sub == "group":
            if len(parts) < 4:
                raise ValueError("Uso: columns group <tipo> <grupo>")
            element_type = engine.normalize_type(parts[2])
            group = parts[3]
            column_config.select_group(element_type, group)
            print(f"Grupo {group} selecionado para {element_type}.")
            return False

        if sub in {"set", "add"}:
            if len(parts) < 4:
                raise ValueError(f"Uso: columns {sub} <tipo> <colunas...>")
            element_type = engine.normalize_type(parts[2])
            requested = parts[3:]

            if sub == "set":
                column_config.set(element_type, requested)
            else:
                column_config.add(element_type, requested)

            print(f"Colunas configuradas para {element_type}:")
            for c in column_config.get(element_type):
                print(f"  {c}")
            return False

        element_type = engine.normalize_type(" ".join(parts[1:]))
        print(f"Colunas atuais para {element_type}:")
        for c in column_config.get(element_type):
            print(f"  {c}")
        return False

    if cmd == "extract-all":
        print("Ação pesada explicitamente solicitada.")
        for element_type, _ in engine.available_types():
            n = engine.select_type(selection, element_type)
            print(f"{element_type}: {n}")
        print("Todos os IDs foram selecionados.")
        return False

    if cmd == "export":
        if selection.count() == 0:
            print("A seleção está vazia.")
            return False

        print("Extraindo SOMENTE os IDs selecionados...")
        selected_groups = extraction.extract_selected(selection.selected)

        default = source.with_name(
            f"{source.stem}_modelbuilder_scenario_{context.selected_scenario_id}.xlsx"
        )

        raw_out = input(
            f"Arquivo [ENTER = {default.name}]: "
        ).strip()

        output = validate_output_path(raw_out, default)

        export_modelbuilder(
            selected_groups,
            output,
            selection_name=selection.name,
            scenario_id=context.selected_scenario_id,
            column_config=column_config,
        )
        print(f"Exportado:\n{output}")
        return False

    print(f'Comando "{parts[0]}" não reconhecido. Digite "help".')
    return False


def main():
    print("=" * 72)
    print(" WATERGEMS LAZY SELECTION + MODELBUILDER EXPORTER V2.5.4")
    print("=" * 72)

    source = ask_sqlite_path()

    try:
        db, model_repo, query_repo, extraction, context, topology_resolver = open_repository(source)
    except Exception as exc:
        print(f"\nNão foi possível abrir o modelo:\n{exc}")
        input("\nPressione ENTER para finalizar...")
        return

    try:
        engine = LazySelectionEngine(model_repo, query_repo, topology_resolver)
        selection = engine.new_selection("ModelBuilder Selection")
        column_config = ColumnConfig()
        field_discovery = DynamicFieldDiscovery(model_repo.schema)
        for element_type, _ in engine.available_types():
            column_config.initialize_type(
                element_type,
                field_discovery.fields_for_type(element_type),
            )

        print("\nModelo aberto. Nenhum elemento foi extraído.")
        print_help()

        while True:
            raw = input("\nlazy> ").strip()
            if not raw:
                continue

            try:
                should_quit = run_command(
                    raw, engine, selection, source, extraction, context, column_config
                )
                if should_quit:
                    break
            except KeyboardInterrupt:
                print("\nComando cancelado.")
            except Exception as exc:
                print(f"Erro: {exc}")
                print('O programa continua aberto. Digite "help" se necessário.')

    finally:
        db.close()


if __name__ == "__main__":
    main()
