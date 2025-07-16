# Container Bin Packing Result

## INPUTS
- Container volume capacity: 50
- Container weight capacity: 20
- Rotation: free
- Items:

| id | weight | volume | group_id |
|----|--------|--------|----------|
| 1 | 1 | 25 | 1 |
| 2 | 2 | 20 | 1 |
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
- Minimum containers used: 5
- Total group splits (penalized): 1

### Container 1
| Item id | Weight | Volume | Group id |
|---------|--------|--------|----------|
| 6 | 1 | 2 | 2 |
| 7 | 2 | 4 | 2 |
| 8 | 1 | 2 | 2 |
| 9 | 2 | 4 | 2 |
| 10 | 1 | 2 | 2 |
| 16 | 3 | 5 | 4 |
| 17 | 1 | 2 | 4 |
| 18 | 3 | 5 | 4 |
| 19 | 1 | 2 | 4 |
| 20 | 3 | 5 | 4 |
| 44 | 2 | 3 | None |
**Total for container 1: weight = 20 (100.0% of max), volume = 36 (72.0% of max)**

### Container 2
| Item id | Weight | Volume | Group id |
|---------|--------|--------|----------|
| 2 | 2 | 20 | 1 |
| 28 | 2 | 3 | None |
| 36 | 2 | 3 | None |
| 40 | 2 | 3 | None |
| 48 | 2 | 3 | None |
| 36 | 2 | 3 | None |
| 38 | 1 | 1 | None |
| 40 | 2 | 3 | None |
| 44 | 2 | 3 | None |
| 48 | 2 | 3 | None |
**Total for container 2: weight = 19 (95.0% of max), volume = 45 (90.0% of max)**

### Container 3
| Item id | Weight | Volume | Group id |
|---------|--------|--------|----------|
| 11 | 1 | 1 | 3 |
| 12 | 1 | 1 | 3 |
| 13 | 1 | 1 | 3 |
| 14 | 1 | 1 | 3 |
| 15 | 1 | 1 | 3 |
| 21 | 2 | 3 | 5 |
| 22 | 1 | 2 | 5 |
| 23 | 2 | 3 | 5 |
| 24 | 1 | 2 | 5 |
| 25 | 2 | 3 | 5 |
| 26 | 1 | 1 | None |
| 34 | 1 | 1 | None |
| 38 | 1 | 1 | None |
| 46 | 1 | 1 | None |
**Total for container 3: weight = 17 (85.0% of max), volume = 22 (44.0% of max)**

### Container 4
| Item id | Weight | Volume | Group id |
|---------|--------|--------|----------|
| 1 | 1 | 25 | 1 |
| 3 | 1 | 2 | 1 |
| 4 | 2 | 3 | 1 |
| 5 | 1 | 2 | 1 |
| 29 | 1 | 2 | None |
| 30 | 1 | 1 | None |
| 32 | 2 | 3 | None |
| 37 | 1 | 2 | None |
| 39 | 1 | 2 | None |
| 41 | 1 | 2 | None |
| 42 | 1 | 1 | None |
| 47 | 1 | 2 | None |
**Total for container 4: weight = 14 (70.0% of max), volume = 47 (94.0% of max)**

### Container 5
| Item id | Weight | Volume | Group id |
|---------|--------|--------|----------|
| 27 | 1 | 2 | None |
| 31 | 1 | 2 | None |
| 33 | 1 | 2 | None |
| 35 | 1 | 2 | None |
| 42 | 1 | 1 | None |
| 43 | 1 | 2 | None |
| 45 | 1 | 2 | None |
| 47 | 1 | 2 | None |
| 49 | 1 | 2 | None |
| 34 | 1 | 1 | None |
| 35 | 1 | 2 | None |
| 37 | 1 | 2 | None |
| 39 | 1 | 2 | None |
| 41 | 1 | 2 | None |
| 43 | 1 | 2 | None |
| 45 | 1 | 2 | None |
| 46 | 1 | 1 | None |
| 49 | 1 | 2 | None |
| 50 | 1 | 1 | None |
**Total for container 5: weight = 19 (95.0% of max), volume = 34 (68.0% of max)**

### Group Splits
| Group id | Containers used | Splits (penalized) | Container numbers |
|----------|----------------|--------------------|-------------------|
| 1 | 2 | 1 | 2, 4 |
| 2 | 1 | 0 | 1 |
| 3 | 1 | 0 | 3 |
| 4 | 1 | 0 | 1 |
| 5 | 1 | 0 | 3 |
