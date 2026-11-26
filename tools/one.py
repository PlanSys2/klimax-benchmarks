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

"""One engine on one problem of generators/temporal.py, through unified-planning.

Usage: one.py ENGINE FAMILY SIZE TIMEOUT     (ENGINE: any engine of unified-planning that
                                             takes the problem: klimax, aries...)
Prints "found seconds actions makespan" when the plan is out, then "STATUS seconds actions
makespan VALID": seconds of the solver alone; VALID is what Klimax's verifier (klimax-val)
says of the plan, whoever found it.
"""
import sys
import time

from unified_planning.plans import TimeTriggeredPlan
from unified_planning.shortcuts import OneshotPlanner, PlanValidator, get_environment

import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generators"))
import temporal  # noqa: E402
import up_klimax  # noqa: E402

up_klimax.register()
get_environment().credits_stream = None
engine, domain, size, timeout = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
problem = temporal.DOMAINS[domain](size, size)
start = time.time()
try:
    with OneshotPlanner(name=engine) as planner:
        result = planner.solve(problem, timeout=timeout)
except Exception as e:  # noqa: BLE001
    print("error", round(time.time() - start, 3), "-", "-", type(e).__name__, str(e)[:160])
    sys.exit(0)
seconds = round(time.time() - start, 3)
if result.plan is None:
    print(result.status.name, seconds, "-", "-", "-", flush=True)
    sys.exit(0)
flat = result.plan.action_plan
if isinstance(flat, TimeTriggeredPlan):
    actions = len(flat.timed_actions)
    makespan = float(max((s + (d or 0) for s, _, d in flat.timed_actions), default=0))
else:
    actions, makespan = len(flat.actions), float(len(flat.actions))
print("found", seconds, actions, round(makespan, 3), flush=True)
with PlanValidator(name="klimax-val") as validator:
    checked = validator.validate(problem, result.plan)
print(result.status.name, seconds, actions, round(makespan, 3), checked.status.name,
      (checked.log_messages[-1].message[:120] if checked.log_messages else ""), flush=True)
