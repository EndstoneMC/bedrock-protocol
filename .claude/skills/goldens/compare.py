"""Judge each golden case of a folder against one BDS run: the bytes BDS wrote back and the JSON it printed."""

import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "tests"))

from conftest import CaseForm, schema_of

folder, run = Path(sys.argv[1]), Path(sys.argv[2])
module = importlib.import_module(f"bedrock_protocol.{folder.name}")
results = {(each["stem"], each["index"]): each for each in json.loads((run / "results.json").read_text())}
declared = {
    declaration["name"]: declaration
    for declaration in (json.loads(each.read_text()) for each in (run / "dump" / "protocol").glob("[pt]*/*.json"))
}
packets = {declaration["id"]: name for name, declaration in declared.items() if "id" in declaration}
total = frozen = 0
for path in sorted(folder.glob("*.json")):
    for index, case in enumerate(json.loads(path.read_text())):
        result = results.get((path.stem, index))
        sent, written = case["bytes"], result and result.get("bds_bytes", "")
        problems = []
        if result is None:
            problems.append("no result in the run")
        elif "crash" in result:
            problems.append(f"crashed: {result['crash']}")
        elif not result["read_ok"]:
            problems.append(f"refused: {result.get('error')}, read {result['consumed']} of {len(sent) // 2} bytes")
        else:
            if result["consumed"] != len(sent) // 2:
                problems.append(f"read {result['consumed']} of {len(sent) // 2} bytes")
            if written != sent:
                at = (
                    next(
                        (i for i, pair in enumerate(zip(sent, written, strict=False)) if pair[0] != pair[1]),
                        min(len(sent), len(written)),
                    )
                    // 2
                )
                problems.append(f"rewritten at byte {at}: case {sent[at * 2 :][:16]}, BDS {written[at * 2 :][:16]}")
            if "bds_json_error" in result:
                problems.append(f"printed no JSON: {result['bds_json_error']}")
            else:
                try:
                    bedrock = CaseForm.parse_bedrock(result["bds_json"])
                except ValueError as error:
                    problems.append(f"printed unreadable JSON: {error}")
                else:
                    if found := CaseForm.locate(
                        case["value"],
                        bedrock,
                        schema_of(module, module.packets[int(path.stem[:3])]),
                        declared,
                        packets.get(int(path.stem[:3])),
                    ):
                        where, ours, theirs = found
                        problems.append(
                            f"JSON differs at {where or '<packet>'}: case {json.dumps(ours)[:100]},"
                            f" BDS {json.dumps(theirs, default=list)[:100]}"
                        )
        total += 1
        frozen += not problems
        sys.stdout.write(f"{path.stem}[{case['id']}]: {'; '.join(problems) or 'freezes'}\n")
sys.stdout.write(f"{frozen} of {total} cases freeze, {total - frozen} do not\n")
sys.exit(frozen != total)
