import random
import numpy as np


MAP = {
    "5x5":["+---------+",
    "| : : : : |",
    "| : : : : |",
    "| : : : : |",
    "| : : : : |",
    "| : : : : |",
    "+---------+"],
    "6x6":
   ["+-----------+",
    "| : : : : : |",
    "| : : : : : |",
    "| : : : : : |",
    "| : : : : : |",
    "| : : : : : |",
    "| : : : : : |",
    "+-----------+"],
    "7x7":
   ["+-------------+",
    "| : : : : : : |",
    "| : : : : : : |",
    "| : : : : : : |",
    "| : : : : : : |",
    "| : : : : : : |",
    "| : : : : : : |",
    "| : : : : : : |",
    "+-------------+"]
    
}

def generate_random_map(random_maps):
    size = random.randint(5, 7)
    index_concatenated = str(size) + "x" + str(size)
    random_map = random_maps[index_concatenated]
    
    
    desc = np.asarray(random_map, dtype='c')
    
    no_of_walls = 0
    no_of_traffic_jams = 0
    restaurant = False
    bloc_A = False
    bloc_B = False
    bloc_C = False
    
    tuples_used_array = []     
            
    while (no_of_walls != (size - 2) or no_of_traffic_jams != (size - 2) or restaurant == False or bloc_A == False or bloc_B == False or bloc_C == False):
            row = random.randint(1, len(desc)-2)
            col = random.randint(1,len(desc[row])-2)

            if (row,col) in tuples_used_array:
                continue
            else:
                tuples_used_array.append((row,col))
            
                 
            if desc[row, col] == b":" and no_of_walls != (size - 2):
                desc[row, col] = random.choice([b"|", b":"])
                if desc[row,col] == b"|":
                    no_of_walls += 1
            if desc[row, col] == b" ":
                cell_contents = b" "
            
                if restaurant == False:
                    cell_contents = b"R"
                    restaurant = True
                elif bloc_A == False:
                    cell_contents = b"A"
                    bloc_A = True
                elif bloc_B == False:
                    cell_contents = b"B"
                    bloc_B = True
                elif bloc_C == False:
                    cell_contents = b"C"
                    bloc_C = True
                elif no_of_traffic_jams < (size - 2):
                    cell_contents = b"X"
                    no_of_traffic_jams += 1
                desc[row, col] = cell_contents
                
    return desc,size

