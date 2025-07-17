# Container Bin Packing Result

## INPUTS
- Container volume capacity: 1000
- Container weight capacity: 40
- Items:

| id | weight | volume | rotation | group_id |
|----|--------|--------|----------|----------|
| 1 | 1 | 250 | None | 1 |
| 2 | 2 | 64 | None | 1 |
| 3 | 1 | 27 | None | 1 |
| 4 | 2 | 8 | None | 1 |

---
## OUTPUTS
Step 1 Solver status: OPTIMAL
- Minimum containers used: 1
- Total group splits (penalized): 0

### Container 1
| Item id | Weight | Volume | Group id |
|---------|--------|--------|----------|
| 1 | 1 | 250 | 1 |
| 2 | 2 | 64 | 1 |
| 3 | 1 | 27 | 1 |
| 4 | 2 | 8 | 1 |
**Total for container 1: weight = 6 (15.0% of max), volume = 349 (34.9% of max)**

### Group Splits
| Group id | Containers used | Splits (penalized) | Container numbers |
|----------|----------------|--------------------|-------------------|
| 1 | 1 | 0 | 1 |
