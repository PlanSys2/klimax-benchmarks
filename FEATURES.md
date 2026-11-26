# What each family uses

| | `transport` | `satellite` | `workshop` | `cellar` |
|---|---|---|---|---|
| Initial task network | partial order | partial order | partial order | partial order |
| Methods | total order | total order | total order | partial order |
| Recursive tasks | yes | no | no | no |
| Method preconditions | yes | yes | yes | yes |
| Parameters that a method leaves free | truck, places | site | no | match |
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
