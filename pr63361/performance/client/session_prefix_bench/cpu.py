"""Boundary snapshots: persistent process identities, never polling in the window."""
import time


def snapshot(root_pid):
    import psutil
    started = time.perf_counter_ns()
    root = psutil.Process(root_pid)
    processes = [root, *root.children(recursive=True)]
    rows = []
    for proc in processes:
        with proc.oneshot():
            cpu = proc.cpu_times()
            # children_* holds CPU of descendants already waited for: a process
            # created and reaped inside the window appears only there.
            rows.append({"pid": proc.pid, "created": proc.create_time(),
                         "name": proc.name(), "cmdline": proc.cmdline(),
                         "cpu_s": cpu.user + cpu.system,
                         "children_s": cpu.children_user + cpu.children_system})
    return {"read_start_ns": started, "processes": rows,
            "read_end_ns": time.perf_counter_ns()}


def delta(before, after, requests):
    def identities(snap):
        return {(r["pid"], r["created"]): r for r in snap["processes"]}
    left, right = identities(before), identities(after)
    if left.keys() != right.keys():
        raise ValueError("Service process tree changed; CPU accounting incomplete")
    totals = {"frontend": 0.0, "engine_core": 0.0, "other_workers": 0.0}
    details = []
    root_pid = before["processes"][0]["pid"]
    for key, row in right.items():
        amount = row["cpu_s"] - left[key]["cpu_s"]
        if amount < 0:
            raise ValueError("CPU counter went backwards")
        reaped = row.get("children_s", 0.0) - left[key].get("children_s", 0.0)
        if reaped > 0:
            raise ValueError(f"Short-lived descendants used {reaped:.2f}s CPU inside the window "
                             "(e.g. uncovered JIT/compile); CPU accounting incomplete")
        label = " ".join([row["name"], *row["cmdline"]])
        group = ("frontend" if row["pid"] == root_pid else
                 "engine_core" if "EngineCore" in label else "other_workers")
        totals[group] += amount
        details.append({"pid": row["pid"], "group": group, "cpu_s": amount})
    return {"seconds": totals, "total_seconds": sum(totals.values()),
            "seconds_per_request": sum(totals.values()) / requests,
            "details": details}
