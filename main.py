from pathlib import Path

from database.connection import WaterGemsDatabase
from database.schema import SchemaInspector
from readers.common import CommonReader
from readers.scenario_aware import ScenarioAwareReaders
from scenario.scenario_reader import ScenarioReader
from scenario.resolver import AlternativeResolver

from extractors.pipe import PipeExtractor
from extractors.node import NodeExtractor
from extractors.tank import TankExtractor
from extractors.directed import DirectedNodeExtractor

from validator import validate
from exporter import export_excel


def choose_scenario(reader):
    scenarios = reader.tree_order()
    if not scenarios:
        raise RuntimeError("Nenhum cenário encontrado no banco.")

    active_id = reader.active_scenario_id()

    print()
    print("=" * 72)
    print("CENÁRIOS ENCONTRADOS")
    print("=" * 72)

    for index, scenario in enumerate(scenarios, start=1):
        indent = "    " * scenario.depth
        marker = " [ATIVO]" if scenario.is_active else ""
        branch = "└── " if scenario.depth > 0 else ""
        print(
            f"[{index:>2}] {indent}{branch}{scenario.display_name} "
            f"(ID {scenario.id}){marker}"
        )

    while True:
        raw = input(
            "\nEscolha o cenário [ENTER = cenário ativo]:\n> "
        ).strip()

        if raw == "":
            if active_id is None:
                print("Não há cenário ativo identificado.")
                continue
            return active_id, scenarios

        try:
            choice = int(raw)
        except ValueError:
            print("Digite o número da lista.")
            continue

        if 1 <= choice <= len(scenarios):
            return scenarios[choice - 1].id, scenarios

        print("Opção inválida.")


def extract_all(sqlite_path):
    with WaterGemsDatabase(sqlite_path) as db:
        schema = SchemaInspector(db)
        common = CommonReader(db, schema)

        scenario_reader = ScenarioReader(db, schema)
        selected_id, scenario_list = choose_scenario(scenario_reader)

        resolver = AlternativeResolver(db, schema)
        context = resolver.build_context(selected_id)
        readers = ScenarioAwareReaders(resolver)

        args = (db, schema, common, readers, context)

        groups = {}
        stats_map = {}

        pipes, pipe_stats = PipeExtractor(*args).extract_all()
        groups["Pipe"] = pipes
        stats_map["Pipe"] = pipe_stats

        node_groups, node_stats = NodeExtractor(*args).extract_all()
        groups.update(node_groups)
        stats_map.update(node_stats)

        tank_groups, tank_stats = TankExtractor(*args).extract_all()
        groups.update(tank_groups)
        stats_map.update(tank_stats)

        directed_groups, directed_stats = DirectedNodeExtractor(*args).extract_all()
        groups.update(directed_groups)
        stats_map.update(directed_stats)

        node_lookup = {}
        for elements in groups.values():
            for e in elements:
                if hasattr(e, "x_ft"):
                    node_lookup[e.id] = (e.label, e.element_type)

        for p in groups.get("Pipe", []):
            p.start_node_label, p.start_node_type = node_lookup.get(
                p.start_node_id, ("", "Not found")
            )
            p.end_node_label, p.end_node_type = node_lookup.get(
                p.end_node_id, ("", "Not found")
            )

        return groups, stats_map, context, scenario_list


def ask_input():
    while True:
        raw = input(
            "\nCaminho do arquivo .wtg.sqlite:\n> "
        ).strip().strip('"').strip("'")
        path = Path(raw)

        if path.exists() and path.is_file():
            return path

        print("Arquivo não encontrado.")


def ask_output(source, scenario_id):
    default = source.with_name(
        f"{source.stem}_scenario_{scenario_id}_export.xlsx"
    )

    raw = input(
        f"\nArquivo de saída [ENTER = {default.name}]:\n> "
    ).strip()

    if not raw:
        return default

    raw = raw.strip('"').strip("'")
    path = Path(raw)

    if path.suffix.lower() != ".xlsx":
        path = path / default.name

    return path


def main():
    print("=" * 72)
    print("   WATERGEMS EXTRACTOR - SCENARIO AWARE V2.1")
    print("=" * 72)

    source = ask_input()

    try:
        groups, stats_map, context, scenario_list = extract_all(source)
        output = ask_output(source, context.selected_scenario_id)

        report = validate(groups)

        export_excel(
            groups=groups,
            stats_map=stats_map,
            report=report,
            output_path=output,
            source_path=source,
            scenario_context=context,
            scenario_list=scenario_list,
        )

    except Exception as exc:
        print()
        print("=" * 72)
        print("ERRO")
        print("=" * 72)
        print(exc)
        input("\nPressione ENTER para finalizar...")
        return

    print()
    print("=" * 72)
    print("EXTRAÇÃO CONCLUÍDA")
    print("=" * 72)
    print(f"Cenário selecionado: {context.selected_scenario_id}")
    print(f"Cenário ativo:       {context.active_scenario_id}")
    print()

    for name, stat in stats_map.items():
        print(
            f"{name}: exportados={stat.exported}, "
            f"ativos={stat.active}, "
            f"inativos={stat.inactive}, "
            f"sem resolução={stat.unresolved_active_topology}"
        )

    print()
    print(f"Excel criado em:\n{output}")

    input("\nPressione ENTER para finalizar...")


if __name__ == "__main__":
    main()
