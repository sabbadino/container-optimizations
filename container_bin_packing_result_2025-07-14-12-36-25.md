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
  - Container 0: items ['21(group_id=5)', '22(group_id=5)', '23(group_id=5)', '24(group_id=5)', '25(group_id=5)', '46(group_id=None)', '50(group_id=None)'], total loaded weight: 10 (50.0% of max), total loaded volume: 15 (30.0% of max)
  - Container 3: items ['1(group_id=1)', '2(group_id=1)', '3(group_id=1)', '4(group_id=1)', '5(group_id=1)', '16(group_id=4)', '17(group_id=4)', '18(group_id=4)', '19(group_id=4)', '20(group_id=4)', '38(group_id=None)'], total loaded weight: 19 (95.0% of max), total loaded volume: 32 (64.0% of max)
  - Container 8: items ['6(group_id=2)', '7(group_id=2)', '8(group_id=2)', '9(group_id=2)', '10(group_id=2)', '11(group_id=3)', '12(group_id=3)', '13(group_id=3)', '14(group_id=3)', '15(group_id=3)', '28(group_id=None)', '32(group_id=None)', '44(group_id=None)', '48(group_id=None)'], total loaded weight: 20 (100.0% of max), total loaded volume: 31 (62.0% of max)
  - Container 49: items ['26(group_id=None)', '27(group_id=None)', '29(group_id=None)', '30(group_id=None)', '31(group_id=None)', '33(group_id=None)', '34(group_id=None)', '35(group_id=None)', '36(group_id=None)', '37(group_id=None)', '39(group_id=None)', '40(group_id=None)', '41(group_id=None)', '42(group_id=None)', '43(group_id=None)', '45(group_id=None)', '47(group_id=None)', '49(group_id=None)'], total loaded weight: 20 (100.0% of max), total loaded volume: 34 (68.0% of max)