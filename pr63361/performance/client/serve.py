# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Start one benchmark server using the supplied argument list."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", choices=("baseline", "token-reuse"), required=True)
    parser.add_argument("--server-python", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18261)
    parser.add_argument("--server-cpus", default="0-11")
    parser.add_argument("--log-level", choices=("INFO", "DEBUG"))
    parser.add_argument("--print-command", action="store_true")
    args = parser.parse_args()
    config = json.loads((Path(__file__).resolve().parents[1] /
                         "server-arguments.json").read_text())
    stage = "N" if args.condition == "baseline" else "V1"
    selected = config["commands"][stage]
    argv = [value.replace("{PYTHON}", str(args.server_python.absolute()))
            .replace("{MODEL_DIR}", str(args.model_dir.resolve()))
            for value in selected["argv"]]
    argv[argv.index("--port") + 1] = str(args.port)
    argv[argv.index("-c") + 1] = args.server_cpus
    semantic_env = dict(selected["semantic_environment"])
    if args.log_level:
        semantic_env["VLLM_LOGGING_LEVEL"] = args.log_level
    env = dict(os.environ, **semantic_env)
    env["PATH"] = str(args.server_python.absolute().parent) + os.pathsep + env.get("PATH", os.defpath)
    if args.print_command:
        print(json.dumps({"argv": argv,
                          "environment": dict(semantic_env, PATH=env["PATH"])}, indent=2))
        return
    if not args.server_python.is_file() or not args.model_dir.is_dir():
        raise ValueError("Provide an installed server Python and local model directory")
    # Remain a foreground process; the caller owns logging and shutdown.
    os.execvpe(argv[0], argv, env)


if __name__ == "__main__":
    main()
