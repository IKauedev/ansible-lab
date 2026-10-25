#!/usr/bin/env python3
"""Inventário dinâmico: gera hosts a partir dos containers Docker do lab.

Considera containers em execução com o label `ansible.group`. O host recebe o
hostname do container, e a porta SSH vem do mapeamento da porta 22/tcp.
"""
import json
import subprocess
import sys

GROUP_LABEL = "ansible.group"


def docker_json(*args):
    out = subprocess.run(["docker", *args], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def build_inventory():
    ids = subprocess.run(
        ["docker", "ps", "-q", "--filter", f"label={GROUP_LABEL}"],
        capture_output=True, text=True, check=True,
    ).stdout.split()

    inventory = {"_meta": {"hostvars": {}}, "lab": {"children": []}}
    if not ids:
        return inventory

    for c in docker_json("inspect", *ids):
        name = c["Config"]["Hostname"]
        group = c["Config"]["Labels"][GROUP_LABEL]
        bindings = c["NetworkSettings"]["Ports"].get("22/tcp") or []
        if not bindings:
            continue

        inventory.setdefault(group, {"hosts": []})["hosts"].append(name)
        if group not in inventory["lab"]["children"]:
            inventory["lab"]["children"].append(group)
        inventory["_meta"]["hostvars"][name] = {
            "ansible_host": "127.0.0.1",
            "ansible_port": int(bindings[0]["HostPort"]),
            "container_name": c["Name"].lstrip("/"),
        }
    return inventory


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--host":
        print(json.dumps({}))  # hostvars já vêm em _meta
        return
    print(json.dumps(build_inventory(), indent=2))


if __name__ == "__main__":
    main()
