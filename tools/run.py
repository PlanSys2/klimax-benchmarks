#!/usr/bin/env python3
# Copyright 2026 Intelligent Robotics Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Runs engines of unified-planning on the temporal hierarchical problems of
generators/temporal.py (one.py runs each): the same time per problem for the whole process,
one core and 8 GB each. Every plan is checked by Klimax's verifier (klimax-val).

Usage: run.py [--engines klimax,aries] [--timeout S] [--jobs N] [--cpus a-b]
              [--out FILE.csv] [--filter REGEX] [--python PYTHON]
`--python` is the interpreter that has unified-planning, up-klimax and the engines (default:
this one).
"""
import argparse
import concurrent.futures
import csv
import os
import queue
import re
import resource
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable
ENV = dict(os.environ)
CPUS = queue.Queue()
MEMORY = 8 << 30


def limit():  # as run_htn.py: 8 GB of address space per run
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY, MEMORY))


def run(job):
    engine, domain, size, timeout = job
    problem = f'p{size:02d}'
    cpu = CPUS.get()
    cmd = ['taskset', '-c', str(cpu), PYTHON, os.path.join(HERE, 'one.py'),
           engine, domain, str(size), str(timeout)]
    start = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                         env=ENV, start_new_session=True, preexec_fn=limit)
    found = None  # the wall time at which the plan was out
    lines = []
    seen = threading.Event()

    def stop():  # Aries does not always stop at its timeout
        if not seen.is_set() and p.poll() is None:
            os.killpg(p.pid, 9)
    timer = threading.Timer(timeout + 2, stop)
    timer.start()
    try:
        # The plan counts if it is out in time; its verification afterwards is not timed
        while True:
            line = p.stdout.readline()
            if not line:
                break
            lines.append(line.split())
            if lines[-1][0] == 'found':
                found = time.time() - start
                seen.set()
        p.wait(timeout=120)
    except subprocess.TimeoutExpired:
        pass
    finally:
        timer.cancel()
        if p.poll() is None:
            os.killpg(p.pid, 9)
        CPUS.put(cpu)
    last = lines[-1] if lines else ['failed', '0', '-', '-']
    if found is None:
        status = 'timeout' if last[0] == 'TIMEOUT' or time.time() - start >= timeout else \
            'failed:' + last[0]
        return engine, domain, problem, status, min(time.time() - start, timeout), '', '', ''
    if found > timeout:
        return engine, domain, problem, 'timeout', timeout, '', '', ''
    status = 'solved' if last[4] == 'VALID' else 'invalid' if last[4] == 'INVALID' else \
        'unverified'
    return engine, domain, problem, status, found, last[2], last[3], last[1]


ap = argparse.ArgumentParser()
ap.add_argument('--engines', default='klimax,aries')
ap.add_argument('--timeout', type=float, default=30.0)
ap.add_argument('--jobs', type=int, default=6)
ap.add_argument('--cpus', default='0-5')
ap.add_argument('--out', default='')
ap.add_argument('--filter', default='')
ap.add_argument('--python', default=sys.executable)
args = ap.parse_args()
PYTHON = args.python
lo, hi = (int(x) for x in args.cpus.split('-'))
for c in list(range(lo, hi + 1))[:args.jobs]:
    CPUS.put(c)
sys.path.insert(0, os.path.join(HERE, '..', 'generators'))
import temporal  # noqa: E402

jobs = [(engine, domain, size, args.timeout)
        for engine in args.engines.split(',')
        for domain in temporal.DOMAINS for size in temporal.SIZES
        if re.search(args.filter, f'{domain}/p{size:02d}')]
out = open(args.out, 'w', newline='') if args.out else None
if out:
    csv.writer(out).writerow(
        ['engine', 'domain', 'problem', 'status', 'seconds', 'plan_length', 'makespan',
         'solver_seconds'])
rows = []
with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
    for row in pool.map(run, jobs):
        rows.append(row)
        if out:
            csv.writer(out).writerow(row)
            out.flush()
by = {}
for engine, d, _, s, *_ in rows:
    by.setdefault((engine, d), {}).setdefault(s, 0)
    by[(engine, d)][s] += 1
for key in sorted(by):
    print(*key, by[key])
for engine in args.engines.split(','):
    print(engine, 'solved', sum(v.get('solved', 0) for k, v in by.items() if k[0] == engine),
          'of', sum(sum(v.values()) for k, v in by.items() if k[0] == engine))
