Libraries 
google-or tools , nello specifico CP/SAT
ALNS loop : Adaptive Large Neighborhood Search

inputs :
- container max weight, container size 
- list boxes with : weight, size, possible rotation

phase 1 : 
- constraint 
  - total boxes weight < weight allowed per container 
- optimization
  - minimize num containers 
  - keep boxes same groupid (if any same container) 
  - distribute volume occupation 

no geometry involved 

phase 2: 
- place box in each container 
  - constraint : 
    - obvious : no floating , no boxes compenetration, no boxes out of container 
    - rotation constraints 
  - optimization : maximize boxes with greater volume in the bottom 


outer loop ALNS :  
  given situation of pervious loop: 
  - block some boxes in container placement , other are free to be moved 
  - re-do loop 1 and loop 2
  - check if situation has improved given some optimization targets
  - loop until max num iteration reached or no imporvements after a certain num of iterations