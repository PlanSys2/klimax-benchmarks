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

"""Temporal hierarchical problems, built with unified-planning so that every engine that takes
them gets the same problem: generators with a seed and a size.

  transport  trucks deliver packages over roads of some length; the deliveries are not ordered
  satellite  a satellite takes images of sites that are visible only for a while (timed
             initial literals)
  workshop   pieces go through two machines in order; a machine does one piece at a time
  cellar     fuses are mended by the light of matches that burn for a while: actions that
             must overlap

Usage: temporal.py OUT_DIR     writes OUT_DIR/<family>/domain-pNN.hddl and pNN.hddl
       instances()             -> [(family, name, problem)]
"""
import os
import random
import sys

from unified_planning.io import PDDLWriter
from unified_planning.model.htn import HierarchicalProblem, Method
from unified_planning.shortcuts import (
    BoolType, DurativeAction, EndTiming, Fluent, GlobalStartTiming, IntType, Not, Object,
    OpenTimeInterval, StartTiming, UserType)


def transport(size, seed):
    """`size` + 2 places in a connected road map, about a truck per three packages."""
    rng = random.Random(seed)
    Place, Truck, Package = UserType("place"), UserType("truck"), UserType("package")
    truck_at = Fluent("truck-at", BoolType(), t=Truck, l=Place)
    package_at = Fluent("package-at", BoolType(), p=Package, l=Place)
    inside = Fluent("in", BoolType(), p=Package, t=Truck)
    road = Fluent("road", BoolType(), a=Place, b=Place)
    length = Fluent("road-length", IntType(), a=Place, b=Place)
    p = HierarchicalProblem(f"transport-{size}")
    for f in (truck_at, package_at, inside, road):
        p.add_fluent(f, default_initial_value=False)
    p.add_fluent(length, default_initial_value=1)
    places = [Object(f"place{i}", Place) for i in range(size + 2)]
    trucks = [Object(f"truck{i}", Truck) for i in range(1 + size // 3)]
    packages = [Object(f"package{i}", Package) for i in range(size + 1)]
    p.add_objects(places + trucks + packages)

    drive = DurativeAction("drive", t=Truck, a=Place, b=Place)
    drive.set_fixed_duration(length(drive.a, drive.b))
    drive.add_condition(StartTiming(), truck_at(drive.t, drive.a))
    drive.add_condition(StartTiming(), road(drive.a, drive.b))
    drive.add_effect(StartTiming(), truck_at(drive.t, drive.a), False)
    drive.add_effect(EndTiming(), truck_at(drive.t, drive.b), True)
    load = DurativeAction("load", t=Truck, p=Package, l=Place)
    load.set_fixed_duration(1)
    load.add_condition(StartTiming(), package_at(load.p, load.l))
    load.add_condition(StartTiming(), truck_at(load.t, load.l))
    load.add_condition(OpenTimeInterval(StartTiming(), EndTiming()), truck_at(load.t, load.l))
    load.add_effect(StartTiming(), package_at(load.p, load.l), False)
    load.add_effect(EndTiming(), inside(load.p, load.t), True)
    unload = DurativeAction("unload", t=Truck, p=Package, l=Place)
    unload.set_fixed_duration(1)
    unload.add_condition(StartTiming(), inside(unload.p, unload.t))
    unload.add_condition(StartTiming(), truck_at(unload.t, unload.l))
    unload.add_condition(OpenTimeInterval(StartTiming(), EndTiming()),
                         truck_at(unload.t, unload.l))
    unload.add_effect(StartTiming(), inside(unload.p, unload.t), False)
    unload.add_effect(EndTiming(), package_at(unload.p, unload.l), True)
    for a in (drive, load, unload):
        p.add_action(a)

    get_to = p.add_task("get-to", t=Truck, l=Place)
    deliver = p.add_task("deliver", p=Package, l=Place)
    there = Method("m-there", t=Truck, l=Place)
    there.set_task(get_to, there.t, there.l)
    there.add_precondition(truck_at(there.t, there.l))
    p.add_method(there)
    go = Method("m-drive", t=Truck, a=Place, b=Place, l=Place)
    go.set_task(get_to, go.t, go.l)
    go.add_precondition(truck_at(go.t, go.a))
    go.add_precondition(road(go.a, go.b))
    go.set_ordered(go.add_subtask(drive, go.t, go.a, go.b), go.add_subtask(get_to, go.t, go.l))
    p.add_method(go)
    m = Method("m-deliver", p=Package, a=Place, b=Place, t=Truck)
    m.set_task(deliver, m.p, m.b)
    m.add_precondition(package_at(m.p, m.a))
    m.set_ordered(m.add_subtask(get_to, m.t, m.a), m.add_subtask(load, m.t, m.p, m.a),
                  m.add_subtask(get_to, m.t, m.b), m.add_subtask(unload, m.t, m.p, m.b))
    p.add_method(m)

    # A line through every place, and some more roads; both ways
    def join(a, b):
        n = rng.randint(2, 9)
        for x, y in ((a, b), (b, a)):
            p.set_initial_value(road(x, y), True)
            p.set_initial_value(length(x, y), n)
    order = places[:]
    rng.shuffle(order)
    for a, b in zip(order, order[1:]):
        join(a, b)
    for _ in range(size // 2):
        a, b = rng.sample(places, 2)
        join(a, b)
    for t in trucks:
        p.set_initial_value(truck_at(t, rng.choice(places)), True)
    for k in packages:
        a, b = rng.sample(places, 2)
        p.set_initial_value(package_at(k, a), True)
        p.task_network.add_subtask(deliver, k, b)
        p.add_goal(package_at(k, b))
    return p


def satellite(size, seed):
    """`size` + 1 sites, each visible in a window of time; turning takes long."""
    rng = random.Random(seed)
    Site = UserType("site")
    pointing = Fluent("pointing", BoolType(), s=Site)
    visible = Fluent("visible", BoolType(), s=Site)
    taken = Fluent("taken", BoolType(), s=Site)
    turn_time = Fluent("turn-time", IntType(), a=Site, b=Site)
    p = HierarchicalProblem(f"satellite-{size}")
    for f in (pointing, visible, taken):
        p.add_fluent(f, default_initial_value=False)
    p.add_fluent(turn_time, default_initial_value=10)
    sites = [Object(f"site{i}", Site) for i in range(size + 2)]
    p.add_objects(sites)

    turn = DurativeAction("turn", a=Site, b=Site)
    turn.set_fixed_duration(turn_time(turn.a, turn.b))
    turn.add_condition(StartTiming(), pointing(turn.a))
    turn.add_effect(StartTiming(), pointing(turn.a), False)
    turn.add_effect(EndTiming(), pointing(turn.b), True)
    image = DurativeAction("take-image", s=Site)
    image.set_fixed_duration(2)
    image.add_condition(StartTiming(), pointing(image.s))
    image.add_condition(StartTiming(), visible(image.s))
    image.add_condition(OpenTimeInterval(StartTiming(), EndTiming()), pointing(image.s))
    image.add_condition(OpenTimeInterval(StartTiming(), EndTiming()), visible(image.s))
    image.add_effect(EndTiming(), taken(image.s), True)
    p.add_action(turn)
    p.add_action(image)

    observe = p.add_task("observe", s=Site)
    here = Method("m-here", s=Site)
    here.set_task(observe, here.s)
    here.add_precondition(pointing(here.s))
    here.add_subtask(image, here.s)
    p.add_method(here)
    away = Method("m-turn", s=Site, a=Site)
    away.set_task(observe, away.s)
    away.add_precondition(pointing(away.a))
    away.add_precondition(Not(pointing(away.s)))
    away.set_ordered(away.add_subtask(turn, away.a, away.s), away.add_subtask(image, away.s))
    p.add_method(away)

    for a in sites:
        for b in sites:
            if a != b:
                p.set_initial_value(turn_time(a, b), rng.randint(5, 30))
    p.set_initial_value(pointing(sites[0]), True)
    # Windows wide enough for every site to be reached in some order: each opens at a random
    # time and stays open long
    for s in sites[1:]:
        opens = rng.randint(1, 40 * size)
        p.add_timed_effect(GlobalStartTiming(opens), visible(s), True)
        p.add_timed_effect(GlobalStartTiming(opens + 60 * (size + 2)), visible(s), False)
        p.task_network.add_subtask(observe, s)
        p.add_goal(taken(s))
    return p


def workshop(size, seed):
    """`size` + 1 pieces, each through two of the machines in order."""
    rng = random.Random(seed)
    Piece, Machine = UserType("piece"), UserType("machine")
    free = Fluent("free", BoolType(), m=Machine)
    first = Fluent("first", BoolType(), p=Piece, m=Machine)
    second = Fluent("second", BoolType(), p=Piece, m=Machine)
    done = Fluent("done", BoolType(), p=Piece, m=Machine)
    time = Fluent("time", IntType(), p=Piece, m=Machine)
    p = HierarchicalProblem(f"workshop-{size}")
    p.add_fluent(free, default_initial_value=True)
    for f in (first, second, done):
        p.add_fluent(f, default_initial_value=False)
    p.add_fluent(time, default_initial_value=1)
    machines = [Object(f"machine{i}", Machine) for i in range(2 + size // 3)]
    pieces = [Object(f"piece{i}", Piece) for i in range(size + 1)]
    p.add_objects(machines + pieces)

    process = DurativeAction("process", p=Piece, m=Machine)
    process.set_fixed_duration(time(process.p, process.m))
    process.add_condition(StartTiming(), free(process.m))
    process.add_effect(StartTiming(), free(process.m), False)
    process.add_effect(EndTiming(), free(process.m), True)
    process.add_effect(EndTiming(), done(process.p, process.m), True)
    p.add_action(process)

    make = p.add_task("make", p=Piece)
    m = Method("m-make", p=Piece, a=Machine, b=Machine)
    m.set_task(make, m.p)
    m.add_precondition(first(m.p, m.a))
    m.add_precondition(second(m.p, m.b))
    m.set_ordered(m.add_subtask(process, m.p, m.a), m.add_subtask(process, m.p, m.b))
    p.add_method(m)

    for piece in pieces:
        a, b = rng.sample(machines, 2)
        p.set_initial_value(first(piece, a), True)
        p.set_initial_value(second(piece, b), True)
        for machine in (a, b):
            p.set_initial_value(time(piece, machine), rng.randint(1, 9))
        p.task_network.add_subtask(make, piece)
        p.add_goal(done(piece, b))
    return p


def cellar(size, seed):
    """`size` fuses to mend in a dark cellar, each by the light of a match that burns only for
    a while: mending has to overlap it."""
    rng = random.Random(seed)
    Match, Fuse = UserType("match"), UserType("fuse")
    unused = Fluent("unused", BoolType(), m=Match)
    light = Fluent("light", BoolType(), m=Match)
    mended = Fluent("mended", BoolType(), f=Fuse)
    handfree = Fluent("handfree", BoolType())
    burns = Fluent("burns", IntType(), m=Match)
    p = HierarchicalProblem(f"cellar-{size}")
    p.add_fluent(unused, default_initial_value=True)
    p.add_fluent(light, default_initial_value=False)
    p.add_fluent(mended, default_initial_value=False)
    p.add_fluent(handfree, default_initial_value=True)
    p.add_fluent(burns, default_initial_value=8)
    matches = [Object(f"match{i}", Match) for i in range(size + 1)]
    fuses = [Object(f"fuse{i}", Fuse) for i in range(size)]
    p.add_objects(matches + fuses)

    strike = DurativeAction("light-match", m=Match)
    strike.set_fixed_duration(burns(strike.m))
    strike.add_condition(StartTiming(), unused(strike.m))
    strike.add_effect(StartTiming(), unused(strike.m), False)
    strike.add_effect(StartTiming(), light(strike.m), True)
    strike.add_effect(EndTiming(), light(strike.m), False)
    mend = DurativeAction("mend", f=Fuse, m=Match)
    mend.set_fixed_duration(5)
    mend.add_condition(StartTiming(), handfree())
    mend.add_condition(StartTiming(), light(mend.m))
    mend.add_condition(OpenTimeInterval(StartTiming(), EndTiming()), light(mend.m))
    mend.add_effect(StartTiming(), handfree(), False)
    mend.add_effect(EndTiming(), handfree(), True)
    mend.add_effect(EndTiming(), mended(mend.f), True)
    p.add_action(strike)
    p.add_action(mend)

    fix = p.add_task("fix", f=Fuse)
    m = Method("m-fix", f=Fuse, m=Match)
    m.set_task(fix, m.f)
    m.add_precondition(unused(m.m))
    m.add_subtask(strike, m.m)
    m.add_subtask(mend, m.f, m.m)
    p.add_method(m)
    for match in matches:
        p.set_initial_value(burns(match), rng.randint(6, 9))
    for fuse in fuses:
        p.task_network.add_subtask(fix, fuse)
        p.add_goal(mended(fuse))
    return p


DOMAINS = {"transport": transport, "satellite": satellite, "workshop": workshop,
           "cellar": cellar}
SIZES = range(1, 11)


def instances():
    """Every problem of the benchmark: (domain, name, problem). The seed is the size."""
    return [(d, f"p{n:02d}", make(n, n)) for d, make in DOMAINS.items() for n in SIZES]


if __name__ == "__main__":
    out = sys.argv[1]
    for domain, name, problem in instances():
        os.makedirs(os.path.join(out, domain), exist_ok=True)
        writer = PDDLWriter(problem)
        writer.write_domain(os.path.join(out, domain, f"domain-{name}.hddl"))
        writer.write_problem(os.path.join(out, domain, f"{name}.hddl"))
    print(len(instances()), "problems in", out)
