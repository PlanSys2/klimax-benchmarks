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

"""Hierarchical problems by feature: a family for each feature of HDDL 2.1 that no public
benchmark has, written as HDDL (Unified Planning does not express all of them).

  deliveries  object fluents: where each robot and package is, as an object
  couriers    action costs and a metric to minimize
  lamps       conditional effects: a switch lights some lamps and turns others off
  meetings    orderings between time points: the two talks of a meeting start at once
  shifts      durative methods: a shift may last up to some time
  rooms       constraints on states: a room is lit while someone walks in

Each family has five problems that have a plan, of growing size (p01 to p05, the seed is the
size), and one that has none (p06). expected.tsv says which.

Usage: features.py OUT_DIR    writes OUT_DIR/<family>/domain.hddl, pNN.hddl and expected.tsv
"""
import os
import random
import sys

SIZES = range(1, 6)


def lines(*items):
    return "\n".join(i for i in items if i) + "\n"


# --- deliveries: object fluents ---------------------------------------------------------------

DELIVERIES = """(define (domain deliveries)
 (:requirements :typing :hierarchy :object-fluents :negative-preconditions :equality
  :method-preconditions)
 (:types place robot package)
 (:predicates (road ?a ?b - place) (loaded ?p - package ?r - robot))
 (:functions (loc ?r - robot) - place (where ?p - package) - place)
 (:task deliver :parameters (?p - package ?to - place))
 (:task get-to :parameters (?r - robot ?to - place))
 (:method m-deliver :parameters (?p - package ?to - place ?r - robot ?from - place)
  :task (deliver ?p ?to)
  :precondition (and (= (where ?p) ?from))
  :ordered-subtasks (and (get-to ?r ?from) (pick ?r ?p ?from) (get-to ?r ?to)
   (drop ?r ?p ?to)))
 (:method m-here :parameters (?r - robot ?to - place)
  :task (get-to ?r ?to)
  :precondition (and (= (loc ?r) ?to)))
 (:method m-step :parameters (?r - robot ?to ?from ?mid - place)
  :task (get-to ?r ?to)
  :precondition (and (= (loc ?r) ?from) (road ?from ?mid) (not (= ?from ?to)))
  :ordered-subtasks (and (move ?r ?from ?mid) (get-to ?r ?to)))
 (:action move :parameters (?r - robot ?a ?b - place)
  :precondition (and (= (loc ?r) ?a) (road ?a ?b))
  :effect (and (assign (loc ?r) ?b)))
 (:action pick :parameters (?r - robot ?p - package ?l - place)
  :precondition (and (= (loc ?r) ?l) (= (where ?p) ?l))
  :effect (and (loaded ?p ?r)))
 (:action drop :parameters (?r - robot ?p - package ?l - place)
  :precondition (and (loaded ?p ?r) (= (loc ?r) ?l))
  :effect (and (not (loaded ?p ?r)) (assign (where ?p) ?l)))
)
"""


def road_map(rng, places, extra):
    """A ring of places, both ways, and `extra` roads more."""
    roads = set()
    for i in range(len(places)):
        a, b = places[i], places[(i + 1) % len(places)]
        roads |= {(a, b), (b, a)}
    while extra > 0 and len(places) > 3:
        a, b = rng.sample(places, 2)
        if (a, b) not in roads:
            roads |= {(a, b), (b, a)}
            extra -= 1
    return sorted(roads)


def deliveries(size, solvable=True):
    rng = random.Random(size)
    places = [f"place{i}" for i in range(size + 3)]
    robots = [f"robot{i}" for i in range(1 + size // 2)]
    packages = [f"package{i}" for i in range(size + 1)]
    roads = road_map(rng, places, size)
    if not solvable:  # a place that no road reaches
        places.append("island")
    start = {p: rng.choice(places[:size + 3]) for p in packages}
    target = {p: rng.choice([x for x in places[:size + 3] if x != start[p]]) for p in packages}
    if not solvable:
        target[packages[0]] = "island"
    return lines(
        "(define (problem deliveries-%d) (:domain deliveries)" % size,
        " (:objects %s - place %s - robot %s - package)" % (
            " ".join(places), " ".join(robots), " ".join(packages)),
        " (:htn :subtasks (and %s))" % " ".join(
            f"(deliver {p} {target[p]})" for p in packages),
        " (:init",
        "  " + " ".join(f"(road {a} {b})" for a, b in roads),
        "  " + " ".join(f"(= (loc {r}) {rng.choice(places[:size + 3])})" for r in robots),
        "  " + " ".join(f"(= (where {p}) {start[p]})" for p in packages) + ")",
        " (:goal (and %s)))" % " ".join(f"(= (where {p}) {target[p]})" for p in packages))


# --- couriers: action costs and a metric -----------------------------------------------------

COURIERS = """(define (domain couriers)
 (:requirements :typing :hierarchy :negative-preconditions :method-preconditions
  :action-costs)
 (:types place courier parcel)
 (:predicates (at ?c - courier ?l - place) (parcel-at ?p - parcel ?l - place)
  (carries ?c - courier ?p - parcel) (road ?a ?b - place))
 (:functions (road-cost ?a ?b - place) (total-cost))
 (:task bring :parameters (?p - parcel ?to - place))
 (:task go :parameters (?c - courier ?to - place))
 (:method m-bring :parameters (?p - parcel ?to ?from - place ?c - courier)
  :task (bring ?p ?to)
  :precondition (and (parcel-at ?p ?from))
  :ordered-subtasks (and (go ?c ?from) (take ?c ?p ?from) (go ?c ?to) (leave ?c ?p ?to)))
 (:method m-there :parameters (?c - courier ?to - place)
  :task (go ?c ?to)
  :precondition (and (at ?c ?to)))
 (:method m-ride :parameters (?c - courier ?to ?from ?mid - place)
  :task (go ?c ?to)
  :precondition (and (at ?c ?from) (road ?from ?mid) (not (at ?c ?to)))
  :ordered-subtasks (and (ride ?c ?from ?mid) (go ?c ?to)))
 (:action ride :parameters (?c - courier ?a ?b - place)
  :precondition (and (at ?c ?a) (road ?a ?b))
  :effect (and (not (at ?c ?a)) (at ?c ?b) (increase (total-cost) (road-cost ?a ?b))))
 (:action take :parameters (?c - courier ?p - parcel ?l - place)
  :precondition (and (at ?c ?l) (parcel-at ?p ?l))
  :effect (and (not (parcel-at ?p ?l)) (carries ?c ?p) (increase (total-cost) 1)))
 (:action leave :parameters (?c - courier ?p - parcel ?l - place)
  :precondition (and (at ?c ?l) (carries ?c ?p))
  :effect (and (not (carries ?c ?p)) (parcel-at ?p ?l) (increase (total-cost) 1)))
)
"""


def couriers(size, solvable=True):
    rng = random.Random(100 + size)
    places = [f"place{i}" for i in range(size + 3)]
    couriers_ = [f"courier{i}" for i in range(1 + size // 2)]
    parcels = [f"parcel{i}" for i in range(size + 1)]
    roads = road_map(rng, places, size + 1)
    cost = {}
    for a, b in roads:  # the same both ways
        cost[(a, b)] = cost.get((b, a), rng.randint(1, 9))
    targets = {p: rng.choice(places) for p in parcels}
    starts = {p: rng.choice([x for x in places if x != targets[p]]) for p in parcels}
    extra = ""
    if not solvable:  # a depot with roads out of it and none into it
        extra = "depot - place "
        targets[parcels[0]] = "depot"
        roads.append(("depot", places[0]))
        cost[("depot", places[0])] = 1
    return lines(
        "(define (problem couriers-%d) (:domain couriers)" % size,
        " (:objects %s %s- place %s - courier %s - parcel)" % (
            " ".join(places), extra, " ".join(couriers_), " ".join(parcels)),
        " (:htn :subtasks (and %s))" % " ".join(f"(bring {p} {targets[p]})" for p in parcels),
        " (:init (= (total-cost) 0)",
        "  " + " ".join(f"(road {a} {b}) (= (road-cost {a} {b}) {cost[(a, b)]})"
                        for a, b in roads),
        "  " + " ".join(f"(at {c} {rng.choice(places)})" for c in couriers_),
        "  " + " ".join(f"(parcel-at {p} {starts[p]})" for p in parcels) + ")",
        " (:metric minimize (total-cost)))")


# --- lamps: conditional effects ---------------------------------------------------------------

LAMPS = """(define (domain lamps)
 (:requirements :typing :hierarchy :conditional-effects :method-preconditions)
 (:types lamp switch)
 (:predicates (lit ?l - lamp) (lights ?s - switch ?l - lamp) (cuts ?s - switch ?l - lamp))
 (:task light :parameters (?l - lamp))
 (:method m-lit :parameters (?l - lamp)
  :task (light ?l)
  :precondition (and (lit ?l)))
 (:method m-press :parameters (?l - lamp ?s - switch)
  :task (light ?l)
  :precondition (and (lights ?s ?l))
  :ordered-subtasks (and (press ?s)))
 (:action press :parameters (?s - switch)
  :effect (and
   (forall (?l - lamp) (when (lights ?s ?l) (lit ?l)))
   (forall (?l - lamp) (when (cuts ?s ?l) (not (lit ?l))))))
)
"""


def lamps(size, solvable=True):
    """Switch i lights lamp i and cuts some of the lamps after it: pressed in order, all are
    lit. Without a plan: two lamps whose only switches cut each other."""
    rng = random.Random(200 + size)
    n = 2 * size + 1
    lamps_ = [f"lamp{i}" for i in range(n)]
    switches = [f"switch{i}" for i in range(n)]
    facts = []
    for i in range(n):
        facts.append(f"(lights switch{i} lamp{i})")
        for j in range(i + 1, n):
            if rng.random() < 0.4:
                facts.append(f"(cuts switch{i} lamp{j})")
    if not solvable:
        lamps_ += ["left", "right"]
        switches += ["for-left", "for-right"]
        facts += ["(lights for-left left)", "(cuts for-left right)",
                  "(lights for-right right)", "(cuts for-right left)"]
    tasks = list(lamps_)
    rng.shuffle(tasks)
    return lines(
        "(define (problem lamps-%d) (:domain lamps)" % size,
        " (:objects %s - lamp %s - switch)" % (" ".join(lamps_), " ".join(switches)),
        " (:htn :subtasks (and %s))" % " ".join(f"(light {lamp})" for lamp in tasks),
        " (:init %s)" % " ".join(facts),
        " (:goal (and %s)))" % " ".join(f"(lit {lamp})" for lamp in lamps_))


# --- meetings: orderings between time points ---------------------------------------------------

MEETINGS = """(define (domain meetings)
 (:requirements :typing :hierarchy :durative-actions)
 (:types worker)
 (:predicates (free ?w - worker) (met ?a ?b - worker) (done ?w - worker))
 (:functions (talk-time ?w - worker) (work-time ?w - worker))
 (:task meet :parameters (?a ?b - worker))
 (:task work :parameters (?w - worker))
 (:method m-meet :parameters (?a ?b - worker)
  :task (meet ?a ?b)
  :subtasks (and (x (talk ?a)) (y (talk ?b)) (z (note ?a ?b)))
  :ordering (and (= (start x) (start y)) (< x z) (< y z)))
 (:method m-work :parameters (?w - worker)
  :task (work ?w)
  :subtasks (and (job ?w)))
 (:durative-action talk :parameters (?w - worker) :duration (= ?duration (talk-time ?w))
  :condition (and (at start (free ?w)))
  :effect (and (at start (not (free ?w))) (at end (free ?w))))
 (:durative-action note :parameters (?a ?b - worker) :duration (= ?duration 1)
  :condition (and (at start (free ?a)))
  :effect (and (at end (met ?a ?b))))
 (:durative-action job :parameters (?w - worker) :duration (= ?duration (work-time ?w))
  :condition (and (at start (free ?w)))
  :effect (and (at start (not (free ?w))) (at end (free ?w)) (at end (done ?w))))
)
"""


def meetings(size, solvable=True):
    """Pairs of workers meet, and each worker has a job: the two talks of a meeting start
    together, so neither of the two can be at a job then. Without a plan: a worker meets
    itself, and cannot talk twice at once."""
    rng = random.Random(300 + size)
    workers = [f"worker{i}" for i in range(size + 2)]
    pairs = []
    for _ in range(size):
        a, b = rng.sample(workers, 2)
        pairs.append((a, b))
    if not solvable:
        pairs.append((workers[0], workers[0]))
    tasks = [f"(meet {a} {b})" for a, b in pairs] + [f"(work {w})" for w in workers]
    rng.shuffle(tasks)
    return lines(
        "(define (problem meetings-%d) (:domain meetings)" % size,
        " (:objects %s - worker)" % " ".join(workers),
        " (:htn :subtasks (and %s))" % " ".join(tasks),
        " (:init %s" % " ".join(f"(free {w})" for w in workers),
        "  " + " ".join(f"(= (talk-time {w}) {rng.randint(2, 6)}) "
                        f"(= (work-time {w}) {rng.randint(3, 9)})" for w in workers) + ")",
        " (:goal (and %s)))" % " ".join(
            [f"(met {a} {b})" for a, b in pairs] + [f"(done {w})" for w in workers]))


# --- shifts: durative methods and their durations ---------------------------------------------

SHIFTS = """(define (domain shifts)
 (:requirements :typing :hierarchy :durative-actions :durative-methods)
 (:types worker)
 (:predicates (idle ?w - worker) (done ?w - worker))
 (:functions (job-time ?w - worker) (limit))
 (:task shift :parameters (?a ?b ?c - worker))
 (:durative-method m-shift :parameters (?a ?b ?c - worker)
  :task (shift ?a ?b ?c)
  :duration (<= ?duration (limit))
  :subtasks (and (x (job ?a)) (y (job ?b)) (z (job ?c))))
 (:durative-action job :parameters (?w - worker) :duration (= ?duration (job-time ?w))
  :condition (and (at start (idle ?w)))
  :effect (and (at start (not (idle ?w))) (at end (idle ?w)) (at end (done ?w))))
)
"""


def shifts(size, solvable=True):
    """Shifts of three jobs each, that may last up to a limit: the jobs of a shift have to run
    at once. Without a plan: a shift with the same worker twice, that cannot run its two jobs at
    once, and a limit below their sum."""
    rng = random.Random(400 + size)
    workers = [f"worker{i}" for i in range(3 * size)]
    times = {w: rng.randint(2, 8) for w in workers}
    groups = [workers[3 * i:3 * i + 3] for i in range(size)]
    limit = max(times.values())
    if not solvable:  # its two jobs one after the other last twice the limit
        times[workers[0]] = limit
        groups.append([workers[0], workers[0], workers[1]])
    return lines(
        "(define (problem shifts-%d) (:domain shifts)" % size,
        " (:objects %s - worker)" % " ".join(workers),
        " (:htn :subtasks (and %s))" % " ".join(f"(shift {' '.join(g)})" for g in groups),
        " (:init (= (limit) %d) %s" % (limit, " ".join(f"(idle {w})" for w in workers)),
        "  " + " ".join(f"(= (job-time {w}) {t})" for w, t in times.items()) + ")",
        " (:goal (and %s)))" % " ".join(f"(done {w})" for w in workers))


# --- rooms: constraints on states ---------------------------------------------------------------

ROOMS = """(define (domain rooms)
 (:requirements :typing :hierarchy :method-constraints)
 (:types room)
 (:predicates (open ?r - room) (inside ?r - room) (lit ?r - room) (seen ?r - room))
 (:task visit :parameters (?r - room))
 (:task prepare :parameters (?r - room))
 (:task save :parameters (?r - room))
 (:method m-visit :parameters (?r - room)
  :task (visit ?r)
  :subtasks (and (o (unlock ?r)) (w (walk ?r)) (c (lock ?r)))
  :ordering (and (< o w) (< w c))
  :constraints (and (before w (lit ?r))))
 (:method m-prepare :parameters (?r - room)
  :task (prepare ?r)
  :subtasks (and (switch ?r)))
 (:method m-save :parameters (?r - room)
  :task (save ?r)
  :subtasks (and (dim ?r)))
 (:action unlock :parameters (?r - room) :effect (and (open ?r)))
 (:action walk :parameters (?r - room) :precondition (and (open ?r))
  :effect (and (inside ?r) (seen ?r)))
 (:action lock :parameters (?r - room) :effect (and (not (open ?r)) (not (inside ?r))))
 (:action switch :parameters (?r - room) :effect (and (lit ?r)))
 (:action dim :parameters (?r - room) :effect (and (not (lit ?r))))
)
"""


def rooms(size, solvable=True):
    """Rooms to visit, each lit just before someone walks in, and lights to switch on and to dim
    to save power, none of them ordered: dimming has to wait for the visit. Without a plan: a
    room whose light is dimmed before its visit, and switched on before that."""
    rng = random.Random(500 + size)
    rooms_ = [f"room{i}" for i in range(size + 1)]
    labels = {}
    tasks = []
    for r in rooms_:
        for kind in ("visit", "prepare", "save"):
            labels[(kind, r)] = f"t{len(tasks)}"
            tasks.append((kind, r))
    order = []
    if not solvable:
        r = rooms_[0]
        order = [(labels[("prepare", r)], labels[("save", r)]),
                 (labels[("save", r)], labels[("visit", r)])]
    rng.shuffle(tasks)
    ordering = " :ordering (and %s)" % " ".join(f"(< {a} {b})" for a, b in order) if order else ""
    return lines(
        "(define (problem rooms-%d) (:domain rooms)" % size,
        " (:objects %s - room)" % " ".join(rooms_),
        " (:htn :subtasks (and %s)%s)" % (
            " ".join(f"({labels[t]} ({t[0]} {t[1]}))" for t in tasks), ordering),
        " (:init)",
        " (:goal (and %s)))" % " ".join(f"(seen {r})" for r in rooms_))


FAMILIES = {
    "deliveries": (DELIVERIES, deliveries),
    "couriers": (COURIERS, couriers),
    "lamps": (LAMPS, lamps),
    "meetings": (MEETINGS, meetings),
    "shifts": (SHIFTS, shifts),
    "rooms": (ROOMS, rooms),
}


def instances():
    """Every problem: (family, name, domain, problem, has a plan)."""
    out = []
    for family, (domain, make) in FAMILIES.items():
        for n in SIZES:
            out.append((family, f"p{n:02d}", domain, make(n), True))
        out.append((family, "p06", domain, make(3, solvable=False), False))
    return out


if __name__ == "__main__":
    root = sys.argv[1]
    expected = []
    for family, name, domain, problem, solvable in instances():
        folder = os.path.join(root, family)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "domain.hddl"), "w") as f:
            f.write(domain)
        with open(os.path.join(folder, name + ".hddl"), "w") as f:
            f.write(problem)
        expected.append(f"{family}\t{name}\t{'plan' if solvable else 'none'}")
    with open(os.path.join(root, "expected.tsv"), "w") as f:
        f.write("family\tproblem\texpected\n" + "\n".join(expected) + "\n")
