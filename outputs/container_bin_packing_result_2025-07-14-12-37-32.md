# Container Bin Packing Result

## INPUTS
- Container volume capacity: 50
- Container weight capacity: 20
- Items:

| id | weight | volume | group_id |
|----|--------|--------|----------|
| 1 | 1 | 2 | 1 |
| 2 | 2 | 3 | 1 |
| 3 | 1 | 2 | 1 |
| 4 | 2 | 3 | 1 |
| 5 | 1 | 2 | 1 |
| 6 | 1 | 2 | 2 |
| 7 | 2 | 4 | 2 |
| 8 | 1 | 2 | 2 |
| 9 | 2 | 4 | 2 |
| 10 | 1 | 2 | 2 |
| 11 | 1 | 1 | 3 |
| 12 | 1 | 1 | 3 |
| 13 | 1 | 1 | 3 |
| 14 | 1 | 1 | 3 |
| 15 | 1 | 1 | 3 |
| 16 | 3 | 5 | 4 |
| 17 | 1 | 2 | 4 |
| 18 | 3 | 5 | 4 |
| 19 | 1 | 2 | 4 |
| 20 | 3 | 5 | 4 |
| 21 | 2 | 3 | 5 |
| 22 | 1 | 2 | 5 |
| 23 | 2 | 3 | 5 |
| 24 | 1 | 2 | 5 |
| 25 | 2 | 3 | 5 |
| 26 | 1 | 1 | None |
| 27 | 1 | 2 | None |
| 28 | 2 | 3 | None |
| 29 | 1 | 2 | None |
| 30 | 1 | 1 | None |
| 31 | 1 | 2 | None |
| 32 | 2 | 3 | None |
| 33 | 1 | 2 | None |
| 34 | 1 | 1 | None |
| 35 | 1 | 2 | None |
| 36 | 2 | 3 | None |
| 37 | 1 | 2 | None |
| 38 | 1 | 1 | None |
| 39 | 1 | 2 | None |
| 40 | 2 | 3 | None |
| 41 | 1 | 2 | None |
| 42 | 1 | 1 | None |
| 43 | 1 | 2 | None |
| 44 | 2 | 3 | None |
| 45 | 1 | 2 | None |
| 46 | 1 | 1 | None |
| 47 | 1 | 2 | None |
| 48 | 2 | 3 | None |
| 49 | 1 | 2 | None |
| 50 | 1 | 1 | None |

---
## OUTPUTS
Solver status: OPTIMAL
- Minimum containers used: 4

| Container | Item id | Weight | Volume | Group id |
|-----------|---------|--------|--------|----------|
| 0 | 21 | 2 | 3 | 5 |
| 0 | 22 | 1 | 2 | 5 |
| 0 | 23 | 2 | 3 | 5 |
| 0 | 24 | 1 | 2 | 5 |
| 0 | 25 | 2 | 3 | 5 |
| 0 | 46 | 1 | 1 | None |
| 0 | 50 | 1 | 1 | None |
| **0 (total)** |  | **10** (50.0%) | **15** (30.0%) |  |
| 3 | 1 | 1 | 2 | 1 |
| 3 | 2 | 2 | 3 | 1 |
| 3 | 3 | 1 | 2 | 1 |
| 3 | 4 | 2 | 3 | 1 |
| 3 | 5 | 1 | 2 | 1 |
| 3 | 16 | 3 | 5 | 4 |
| 3 | 17 | 1 | 2 | 4 |
| 3 | 18 | 3 | 5 | 4 |
| 3 | 19 | 1 | 2 | 4 |
| 3 | 20 | 3 | 5 | 4 |
| 3 | 38 | 1 | 1 | None |
| **3 (total)** |  | **19** (95.0%) | **32** (64.0%) |  |
| 8 | 6 | 1 | 2 | 2 |
| 8 | 7 | 2 | 4 | 2 |
| 8 | 8 | 1 | 2 | 2 |
| 8 | 9 | 2 | 4 | 2 |
| 8 | 10 | 1 | 2 | 2 |
| 8 | 11 | 1 | 1 | 3 |
| 8 | 12 | 1 | 1 | 3 |
| 8 | 13 | 1 | 1 | 3 |
| 8 | 14 | 1 | 1 | 3 |
| 8 | 15 | 1 | 1 | 3 |
| 8 | 28 | 2 | 3 | None |
| 8 | 32 | 2 | 3 | None |
| 8 | 44 | 2 | 3 | None |
| 8 | 48 | 2 | 3 | None |
| **8 (total)** |  | **20** (100.0%) | **31** (62.0%) |  |
| 49 | 26 | 1 | 1 | None |
| 49 | 27 | 1 | 2 | None |
| 49 | 29 | 1 | 2 | None |
| 49 | 30 | 1 | 1 | None |
| 49 | 31 | 1 | 2 | None |
| 49 | 33 | 1 | 2 | None |
| 49 | 34 | 1 | 1 | None |
| 49 | 35 | 1 | 2 | None |
| 49 | 36 | 2 | 3 | None |
| 49 | 37 | 1 | 2 | None |
| 49 | 39 | 1 | 2 | None |
| 49 | 40 | 2 | 3 | None |
| 49 | 41 | 1 | 2 | None |
| 49 | 42 | 1 | 1 | None |
| 49 | 43 | 1 | 2 | None |
| 49 | 45 | 1 | 2 | None |
| 49 | 47 | 1 | 2 | None |
| 49 | 49 | 1 | 2 | None |
| **49 (total)** |  | **20** (100.0%) | **34** (68.0%) |  |