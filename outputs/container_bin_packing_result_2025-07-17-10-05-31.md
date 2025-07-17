# Container Bin Packing Result

## INPUTS
- Container volume capacity: 1000
- Container weight capacity: 20
- Rotation: free
- Items:

| id | weight | volume | group_id |
|----|--------|--------|----------|
| 1 | 1 | 125 | 1 |
| 2 | 2 | 64 | 1 |
| 3 | 1 | 27 | 1 |
| 4 | 2 | 8 | 1 |
| 5 | 1 | 1 | 1 |
| 6 | 1 | 125 | 2 |
| 7 | 2 | 64 | 2 |
| 8 | 1 | 27 | 2 |
| 9 | 2 | 64 | 2 |
| 10 | 1 | 27 | 2 |
| 11 | 1 | 8 | 3 |
| 12 | 1 | 8 | 3 |
| 13 | 1 | 8 | 3 |
| 14 | 1 | 8 | 3 |
| 15 | 1 | 8 | 3 |
| 16 | 3 | 125 | 4 |
| 17 | 1 | 8 | 4 |
| 18 | 3 | 125 | 4 |
| 19 | 1 | 8 | 4 |
| 20 | 3 | 125 | 4 |
| 21 | 2 | 27 | 5 |
| 22 | 1 | 8 | 5 |
| 23 | 2 | 27 | 5 |
| 24 | 1 | 8 | 5 |
| 25 | 2 | 27 | 5 |
| 26 | 1 | 1 | None |
| 27 | 1 | 8 | None |
| 28 | 2 | 27 | None |
| 29 | 1 | 8 | None |
| 30 | 1 | 1 | None |
| 31 | 1 | 8 | None |
| 32 | 2 | 27 | None |
| 33 | 1 | 1 | None |
| 34 | 1 | 1 | None |
| 35 | 1 | 8 | None |
| 36 | 2 | 27 | None |
| 37 | 1 | 8 | None |
| 38 | 1 | 1 | None |
| 39 | 1 | 8 | None |
| 40 | 2 | 27 | None |
| 41 | 1 | 8 | None |
| 42 | 1 | 1 | None |
| 43 | 1 | 8 | None |
| 44 | 2 | 27 | None |
| 45 | 1 | 8 | None |
| 46 | 1 | 1 | None |
| 47 | 1 | 8 | None |
| 48 | 2 | 27 | None |
| 49 | 1 | 8 | None |
| 34 | 1 | 1 | None |
| 35 | 1 | 8 | None |
| 36 | 2 | 27 | None |
| 37 | 1 | 8 | None |
| 38 | 1 | 1 | None |
| 39 | 1 | 8 | None |
| 40 | 2 | 27 | None |
| 41 | 1 | 8 | None |
| 42 | 1 | 1 | None |
| 43 | 1 | 8 | None |
| 44 | 2 | 27 | None |
| 45 | 1 | 8 | None |
| 46 | 1 | 1 | None |
| 47 | 1 | 8 | None |
| 48 | 2 | 27 | None |
| 49 | 1 | 8 | None |
| 50 | 1 | 1 | None |

---
## OUTPUTS
Solver status: OPTIMAL
- Minimum containers used: 5
- Total group splits (penalized): 0

### Container 1

| Item id | Weight | Volume | Group id |
|---------|--------|--------|----------|
| 6 | 1 | 125 | 2 |
| 7 | 2 | 64 | 2 |
| 8 | 1 | 27 | 2 |
| 9 | 2 | 64 | 2 |
| 10 | 1 | 27 | 2 |
| 21 | 2 | 27 | 5 |
| 22 | 1 | 8 | 5 |
| 23 | 2 | 27 | 5 |
| 24 | 1 | 8 | 5 |
| 25 | 2 | 27 | 5 |
| 42 | 1 | 1 | None |
| 46 | 1 | 1 | None |
| 48 | 2 | 27 | None |
| 50 | 1 | 1 | None |


**Total for container 1: weight = 20 (100.0% of max), volume = 434 (43.4% of max)**

### Container 2
| Item id | Weight | Volume | Group id |
|---------|--------|--------|----------|
| 11 | 1 | 8 | 3 |
| 12 | 1 | 8 | 3 |
| 13 | 1 | 8 | 3 |
| 14 | 1 | 8 | 3 |
| 15 | 1 | 8 | 3 |
| 40 | 2 | 27 | None |
| 42 | 1 | 1 | None |
| 44 | 2 | 27 | None |
| 48 | 2 | 27 | None |
| 34 | 1 | 1 | None |
| 36 | 2 | 27 | None |
| 38 | 1 | 1 | None |
| 40 | 2 | 27 | None |
| 44 | 2 | 27 | None |
**Total for container 2: weight = 20 (100.0% of max), volume = 205 (20.5% of max)**

### Container 3
| Item id | Weight | Volume | Group id |
|---------|--------|--------|----------|
| 1 | 1 | 125 | 1 |
| 2 | 2 | 64 | 1 |
| 3 | 1 | 27 | 1 |
| 4 | 2 | 8 | 1 |
| 5 | 1 | 1 | 1 |
| 26 | 1 | 1 | None |
| 28 | 2 | 27 | None |
| 30 | 1 | 1 | None |
| 32 | 2 | 27 | None |
| 33 | 1 | 1 | None |
| 34 | 1 | 1 | None |
| 36 | 2 | 27 | None |
| 38 | 1 | 1 | None |
| 46 | 1 | 1 | None |
**Total for container 3: weight = 19 (95.0% of max), volume = 312 (31.2% of max)**

### Container 4
| Item id | Weight | Volume | Group id |
|---------|--------|--------|----------|
| 16 | 3 | 125 | 4 |
| 17 | 1 | 8 | 4 |
| 18 | 3 | 125 | 4 |
| 19 | 1 | 8 | 4 |
| 20 | 3 | 125 | 4 |
**Total for container 4: weight = 11 (55.0% of max), volume = 391 (39.1% of max)**

### Container 5
| Item id | Weight | Volume | Group id |
|---------|--------|--------|----------|
| 27 | 1 | 8 | None |
| 29 | 1 | 8 | None |
| 31 | 1 | 8 | None |
| 35 | 1 | 8 | None |
| 37 | 1 | 8 | None |
| 39 | 1 | 8 | None |
| 41 | 1 | 8 | None |
| 43 | 1 | 8 | None |
| 45 | 1 | 8 | None |
| 47 | 1 | 8 | None |
| 49 | 1 | 8 | None |
| 35 | 1 | 8 | None |
| 37 | 1 | 8 | None |
| 39 | 1 | 8 | None |
| 41 | 1 | 8 | None |
| 43 | 1 | 8 | None |
| 45 | 1 | 8 | None |
| 47 | 1 | 8 | None |
| 49 | 1 | 8 | None |
**Total for container 5: weight = 19 (95.0% of max), volume = 152 (15.2% of max)**

### Group Splits
| Group id | Containers used | Splits (penalized) | Container numbers |
|----------|----------------|--------------------|-------------------|
| 1 | 1 | 0 | 3 |
| 2 | 1 | 0 | 1 |
| 3 | 1 | 0 | 2 |
| 4 | 1 | 0 | 4 |
| 5 | 1 | 0 | 1 |
