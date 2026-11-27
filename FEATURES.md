# What each family uses

| | `transport` | `satellite` | `workshop` | `cellar` |
|---|---|---|---|---|
| Initial task network | partial order | partial order | partial order | partial order |
| Methods | total order | total order | total order | partial order |
| Recursive tasks | yes | no | no | no |
| Method preconditions | yes | yes | yes | yes |
| Parameters that the task does not bind | truck, places | site | no | match |
| Durative actions | yes | yes | yes | yes |
| Durations | a function of the arguments, and constants | a function, and constants | a function | a function, and a constant |
| Conditions over all | yes | yes | no | yes |
| Timed initial literals | no | yes | no | no |
| Actions that may run at once | of different trucks | no | on different machines | yes |
| Actions that must overlap | no | no | no | yes |
| Numeric conditions and effects | no | no | no | no |
| Constraints on times and states (HDDL 2.1) | no | no | no | no |
| State goal | yes | yes | yes | yes |

Sizes: `transport` has `size + 2` places, `size + 1` packages and a truck for every three
packages; `satellite`, `size + 1` sites to image; `workshop`, `size + 1` pieces and a machine
for every three; `cellar`, `size` fuses and one match more.

A parameter that the task does not bind may still be fixed by a static fact of the method's
precondition (as the two machines of a piece in `workshop`): `klimax --check` counts it as
`free-method-parameters` all the same.

# The families by feature

As `klimax --check` reports them (HDDL feature names), besides `typing` and `hierarchy`:

| Family | Features |
|---|---|
| `deliveries` | negative-preconditions, equality, object-fluents, partial-order-initial, recursion, method-preconditions, free-method-parameters, empty-methods, goal |
| `couriers` | negative-preconditions, numeric-fluents, action-costs, metric, metric-fluents, partial-order-initial, recursion, method-preconditions, free-method-parameters, empty-methods |
| `lamps` | conditional-effects, partial-order-initial, method-preconditions, free-method-parameters, empty-methods, goal |
| `meetings` | numeric-fluents, durative-actions, partial-order-initial, partial-order-methods, goal, time-point-orderings |
| `shifts` | numeric-fluents, durative-actions, partial-order-initial, partial-order-methods, goal, durative-methods, method-durations |
| `rooms` | partial-order-initial, goal, state-constraints |
