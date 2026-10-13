#!/usr/bin/env python3
"""长任务的启动与检查。用 PID 文件 + /proc 判断存活，不用 pgrep/ps|grep（那类写法会把查询命令自己算进去）。仅依赖标准库，Linux。

  start  --dir RUNDIR -- 命令...     后台启动；写 pid.json、log.txt；结束时写 exit_code
  status --dir RUNDIR [--stall 秒] [--tail 行数] [--sentinel 文件]
                                      存活？退出码？日志多久没更新？有无报错字样？完成标记在不在？
  wait   --dir RUNDIR [--timeout 秒] [--poll 秒]   等到结束；超时返回 4
status 的退出码：0 运行中且正常 / 0 已正常结束；1 已结束且退出码非零；2 疑似卡住；3 进程消失但没有退出码
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time

ERR = re.compile(r"(Traceback \(most recent call last\)|\bError\b|\bException\b|CUDA out of memory|\bnan\b|Killed)", re.I)


def proc_stat(pid):
    """返回 (状态字母, 启动时刻)；进程不存在返回 (None, None)。启动时刻用于识别 PID 被复用。"""
    try:
        with open("/proc/%d/stat" % pid) as f:
            rest = f.read().rsplit(")", 1)[1].split()
        return rest[0], rest[19]
    except (IOError, OSError, IndexError):
        return None, None


def starttime(pid):
    return proc_stat(pid)[1]


def info(d):
    p = os.path.join(d, "pid.json")
    if not os.path.exists(p):
        sys.exit("找不到 %s（这个目录不是用 jobwatch start 启动的）" % p)
    try:
        with open(p) as f:
            meta = json.load(f)
    except ValueError:
        sys.exit("%s 还没写完或已损坏（任务可能正在启动），稍后再查" % p)
    if not meta.get("starttime"):
        meta["starttime"] = "?"  # 启动后立刻退出的进程拿不到启动时刻，按已结束处理
    return meta


def alive(meta):
    state, st = proc_stat(meta["pid"])
    # 僵尸进程（Z）已经结束，只是还没被回收，不算在运行
    return st is not None and st == meta["starttime"] and state not in ("Z", "X")


def exit_code(d):
    p = os.path.join(d, "exit_code")
    if not os.path.exists(p):
        return None
    t = open(p).read().strip()
    return int(t) if t.lstrip("-").isdigit() else None


def cmd_start(a):
    if not a.command:
        sys.exit("用法: start --dir RUNDIR -- 命令...")
    os.makedirs(a.dir, exist_ok=True)
    leftovers = [f for f in ("exit_code", "log.txt") if os.path.exists(os.path.join(a.dir, f))]
    pidfile = os.path.join(a.dir, "pid.json")
    try:
        # 独占创建：两个 start 同时抢同一个目录时只有一个能成功
        fd = os.open(pidfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except OSError:
        sys.exit("该目录已有 pid.json，换一个目录，避免覆盖上一次运行的证据")
    if leftovers:
        os.close(fd)
        os.unlink(pidfile)
        sys.exit("该目录里有上一次运行留下的 %s；旧退出码会被当成这次的结果。换一个空目录" % "、".join(leftovers))
    # 多个参数：按原样逐个转义后交给 shell，保住引号和空格；单个参数：视为一整条 shell 命令
    cmd = " ".join(shlex.quote(x) for x in a.command) if len(a.command) > 1 else a.command[0]
    log = open(os.path.join(a.dir, "log.txt"), "ab")
    # 用子 shell 包住命令：命令里自己调用 exit 时也能记下退出码
    wrapped = '( %s\n); echo $? > %s' % (cmd, shlex.quote(os.path.join(os.path.abspath(a.dir), "exit_code")))
    try:
        proc = subprocess.Popen(["bash", "-c", wrapped], stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True, cwd=a.cwd or None)
    except Exception:
        os.close(fd)
        os.unlink(pidfile)
        raise
    time.sleep(0.2)
    meta = {"pid": proc.pid, "starttime": starttime(proc.pid), "command": cmd, "argv": a.command,
            "cwd": a.cwd or os.getcwd(), "started_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with os.fdopen(fd, "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print("已启动 pid=%d  日志 %s" % (proc.pid, os.path.join(a.dir, "log.txt")))
    print("启动不等于正常：稍后用 status 确认日志有有效输出")
    return 0


def cmd_status(a):
    meta = info(a.dir)
    is_alive, code = alive(meta), exit_code(a.dir)
    logp = os.path.join(a.dir, "log.txt")
    size = os.path.getsize(logp) if os.path.exists(logp) else 0
    age = time.time() - os.path.getmtime(logp) if os.path.exists(logp) else float("inf")
    lines = []
    if size:
        with open(logp, "rb") as f:
            f.seek(max(0, size - 200000))
            lines = f.read().decode("utf-8", "replace").splitlines()
    errs = [l for l in lines if ERR.search(l)]
    print("命令: %s" % meta["command"])
    print("启动: %s  pid=%d" % (meta["started_at"], meta["pid"]))
    print("进程: %s   退出码: %s" % ("存活" if is_alive else "不存在", "无" if code is None else code))
    print("日志: %d 字节，%.0f 秒前更新；末尾 20 万字节内报错字样 %d 行" % (size, age, len(errs)))
    if a.sentinel:
        print("完成标记 %s: %s" % (a.sentinel, "存在" if os.path.exists(a.sentinel) else "不存在"))
    for l in lines[-a.tail:]:
        print("  | " + l[:200])
    if errs:
        print("最近的报错字样:")
        for l in errs[-3:]:
            print("  ! " + l[:200])
    if not is_alive and code is None:
        print("判定: 进程消失但没有退出码（被杀或机器重启）——不能当作完成")
        return 3
    if not is_alive:
        print("判定: 已结束，退出码 %d%s" % (code, "" if code == 0 else "（失败）"))
        if code == 0 and errs:
            print("      退出码为 0 但日志里有报错字样，需要人工看")
        return 0 if code == 0 else 1
    if a.stall and age > a.stall:
        print("判定: 运行中，但日志已 %.0f 秒没有更新（阈值 %d 秒）——疑似卡住" % (age, a.stall))
        return 2
    print("判定: 运行中" + ("；日志里有报错字样，需要人工看" if errs else ""))
    return 0


def cmd_wait(a):
    meta = info(a.dir)
    t0 = time.time()
    while alive(meta):
        if a.timeout and time.time() - t0 > a.timeout:
            print("等待超时（%d 秒），进程仍在运行" % a.timeout)
            return 4
        time.sleep(a.poll)
    code = exit_code(a.dir)
    print("已结束，退出码 %s" % ("无（异常消失）" if code is None else code))
    return 0 if code == 0 else (3 if code is None else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True
    s = sub.add_parser("start"); s.add_argument("--dir", required=True); s.add_argument("--cwd")
    s.add_argument("command", nargs=argparse.REMAINDER); s.set_defaults(fn=cmd_start)
    s = sub.add_parser("status"); s.add_argument("--dir", required=True); s.add_argument("--stall", type=int)
    s.add_argument("--tail", type=int, default=5); s.add_argument("--sentinel"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("wait"); s.add_argument("--dir", required=True); s.add_argument("--timeout", type=int)
    s.add_argument("--poll", type=float, default=2.0); s.set_defaults(fn=cmd_wait)
    a = ap.parse_args()
    if a.cmd == "start" and a.command and a.command[0] == "--":
        a.command = a.command[1:]
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
