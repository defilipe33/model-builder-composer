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

from selection.engine import SelectionEngine
from modelbuilder.exporter import export_modelbuilder


def choose_scenario(reader):
    scenarios = reader.tree_order()
    active_id = reader.active_scenario_id()

    print("\nCENÁRIOS")
    for i, s in enumerate(scenarios, start=1):
        indent = "    " * s.depth
        marker = " [ATIVO]" if s.is_active else ""
        print(f"[{i:>2}] {indent}{s.display_name} (ID {s.id}){marker}")

    while True:
        raw = input("\nEscolha [ENTER = ativo]: ").strip()
        if not raw and active_id is not None:
            return active_id
        try:
            idx = int(raw)
            if 1 <= idx <= len(scenarios):
                return scenarios[idx - 1].id
        except ValueError:
            pass
        print("Opção inválida.")


def load_model(sqlite_path):
    db = WaterGemsDatabase(sqlite_path)
    schema = SchemaInspector(db)
    common = CommonReader(db, schema)

    scenario_reader = ScenarioReader(db, schema)
    selected_id = choose_scenario(scenario_reader)

    resolver = AlternativeResolver(db, schema)
    context = resolver.build_context(selected_id)
    readers = ScenarioAwareReaders(resolver)

    args = (db, schema, common, readers, context)
    groups = {}

    groups["Pipe"], _ = PipeExtractor(*args).extract_all()

    node_groups, _ = NodeExtractor(*args).extract_all()
    groups.update(node_groups)

    tank_groups, _ = TankExtractor(*args).extract_all()
    groups.update(tank_groups)

    directed_groups, _ = DirectedNodeExtractor(*args).extract_all()
    groups.update(directed_groups)

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

    return db, groups, context


def print_help():
    print("""
COMANDOS

  types
      Lista tipos disponíveis.

  select type Pipe
      Seleciona todos os elementos do tipo.

  select active Pipe true
      Seleciona Pipes pelo Is Active.

  select id 123 456 789
      Seleciona IDs individuais.

  select label P-100 P-101
      Seleciona Labels individuais.

  filter Pipe Physical_PipeMaterial eq "PVC"
  filter Pipe Physical_PipeDiameter gte 0.9842519685
  filter Pipe UDX.SETOR_VRP eq "SETOR 01"
      Seleciona por atributo dinâmico.

  dependencies
      Inclui nós necessários aos Pipes selecionados.

  summary
      Mostra contagens da seleção.

  clear
      Limpa seleção.

  export
      Gera o Excel para ModelBuilder.

  quit
""")


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


def main():
    print("=" * 72)
    print(" WATERGEMS SELECTION ENGINE + MODELBUILDER EXPORTER V1")
    print("=" * 72)

    raw = input("\nCaminho do .wtg.sqlite:\n> ").strip().strip('"').strip("'")
    source = Path(raw)

    db, groups, context = load_model(source)

    try:
        engine = SelectionEngine(groups)
        selection = engine.new_selection("ModelBuilder Selection")

        print_help()

        while True:
            raw = input("\nselection> ").strip()
            if not raw:
                continue

            parts = raw.split()
            cmd = parts[0].lower()

            if cmd == "quit":
                break

            if cmd == "help":
                print_help()

            elif cmd == "types":
                for t in engine.available_types():
                    print(f"{t}: {len(groups[t])}")

            elif cmd == "clear":
                selection.clear()
                print("Seleção limpa.")

            elif cmd == "summary":
                print(f"Total: {selection.count()}")
                for k, v in engine.summary(selection).items():
                    print(f"  {k}: {v}")

            elif cmd == "dependencies":
                added = engine.include_pipe_dependencies(selection)
                print(f"Dependências adicionadas: {added}")

            elif cmd == "select" and len(parts) >= 3:
                mode = parts[1].lower()

                if mode == "type":
                    element_type = " ".join(parts[2:])
                    n = engine.select_filtered(selection, [element_type])
                    print(f"Selecionados: {n}")

                elif mode == "active" and len(parts) >= 4:
                    element_type = parts[2]
                    active = parse_value(parts[3])
                    n = engine.select_filtered(
                        selection,
                        [element_type],
                        [("is_active", "eq", active)],
                    )
                    print(f"Selecionados: {n}")

                elif mode == "id":
                    n = engine.select_ids(selection, [int(x) for x in parts[2:]])
                    print(f"Selecionados: {n}")

                elif mode == "label":
                    n = engine.select_labels(selection, parts[2:])
                    print(f"Selecionados: {n}")

                else:
                    print("Comando select inválido.")

            elif cmd == "filter" and len(parts) >= 5:
                element_type = parts[1]
                field = parts[2]
                op = parts[3]
                value = parse_value(" ".join(parts[4:]))
                n = engine.select_filtered(
                    selection,
                    [element_type],
                    [(field, op, value)],
                )
                print(f"Selecionados: {n}")

            elif cmd == "export":
                if selection.count() == 0:
                    print("A seleção está vazia.")
                    continue

                default = source.with_name(
                    f"{source.stem}_modelbuilder_scenario_{context.selected_scenario_id}.xlsx"
                )
                out = input(
                    f"Arquivo [ENTER = {default.name}]: "
                ).strip().strip('"').strip("'")
                output = Path(out) if out else default

                if output.suffix.lower() != ".xlsx":
                    output = output / default.name

                selected_groups = engine.selected_groups(selection)
                export_modelbuilder(
                    selected_groups,
                    output,
                    selection_name=selection.name,
                    scenario_id=context.selected_scenario_id,
                )
                print(f"Exportado:\n{output}")

            else:
                print("Comando desconhecido. Digite 'help'.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
