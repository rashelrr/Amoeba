import os
import pickle
import numpy as np
import logging
from amoeba_state import AmoebaState
import constants

import random
from typing import Tuple, List
import numpy.typing as npt
import math

MAP_LENGTH = 100
LOW_DENSITY = .1
class Player:
    def __init__(self, rng: np.random.Generator, logger: logging.Logger, metabolism: float, goal_size: int,
                 precomp_dir: str) -> None:
        """Initialise the player with the basic amoeba information

            Args:
                rng (np.random.Generator): numpy random number generator, use this for same player behavior across run
                logger (logging.Logger): logger use this like logger.info("message")
                metabolism (float): the percentage of amoeba cells, that can move
                goal_size (int): the size the amoeba must reach
                precomp_dir (str): Directory path to store/load pre-computation
        """

        # precomp_path = os.path.join(precomp_dir, "{}.pkl".format(map_path))

        # # precompute check
        # if os.path.isfile(precomp_path):
        #     # Getting back the objects:
        #     with open(precomp_path, "rb") as f:
        #         self.obj0, self.obj1, self.obj2 = pickle.load(f)
        # else:
        #     # Compute objects to store
        #     self.obj0, self.obj1, self.obj2 = _

        #     # Dump the objects
        #     with open(precomp_path, 'wb') as f:
        #         pickle.dump([self.obj0, self.obj1, self.obj2], f)

        self.rng = rng
        self.logger = logger
        self.metabolism = metabolism
        self.goal_size = goal_size
        self.current_size = goal_size / 4
        self.shape = 0

        self.amoeba_map = None
        self.periphery = None
        self.bacteria = None
        self.movable_cells = None
        self.num_available_moves = 0
        self.static_center = [50, 50]

        self.turn = 0
    
    # Adapted from G2 aka from amoeba_game.py
    def check_move(
        self, retracts: List[Tuple[int, int]], extends: List[Tuple[int, int]]
    ) -> bool:
        if not set(retracts).issubset(self.periphery):
            return False

        movable = retracts[:]
        new_periphery = list(self.periphery.difference(set(retracts)))
        for i, j in new_periphery:
            nbr = self.find_movable_neighbor(i, j, self.amoeba_map, self.bacteria)
            for x, y in nbr:
                if (x, y) not in movable:
                    movable.append((x, y))

        if not set(extends).issubset(set(movable)):
            return False

        amoeba = np.copy(self.amoeba_map)
        amoeba[amoeba < 0] = 0
        amoeba[amoeba > 0] = 1

        for i, j in retracts:
            amoeba[i][j] = 0

        for i, j in extends:
            amoeba[i][j] = 1

        tmp = np.where(amoeba == 1)
        result = list(zip(tmp[0], tmp[1]))
        check = np.zeros((constants.map_dim, constants.map_dim), dtype=int)

        stack = result[0:1]
        while len(stack):
            a, b = stack.pop()
            check[a][b] = 1

            if (a, (b - 1) % constants.map_dim) in result and check[a][
                (b - 1) % constants.map_dim
            ] == 0:
                stack.append((a, (b - 1) % constants.map_dim))
            if (a, (b + 1) % constants.map_dim) in result and check[a][
                (b + 1) % constants.map_dim
            ] == 0:
                stack.append((a, (b + 1) % constants.map_dim))
            if ((a - 1) % constants.map_dim, b) in result and check[
                (a - 1) % constants.map_dim
            ][b] == 0:
                stack.append(((a - 1) % constants.map_dim, b))
            if ((a + 1) % constants.map_dim, b) in result and check[
                (a + 1) % constants.map_dim
            ][b] == 0:
                stack.append(((a + 1) % constants.map_dim, b))

        return (amoeba == check).all()

    def find_movable_cells(self, retract, periphery, amoeba_map, bacteria, mini):
        movable = []
        new_periphery = list(set(periphery).difference(set(retract)))
        for i, j in new_periphery:
            nbr = self.find_movable_neighbor(i, j, amoeba_map, bacteria)
            for x, y in nbr:
                if (x, y) not in movable:
                    movable.append((x, y))

        movable += retract

        return movable[:mini]

    def find_movable_neighbor(self, x, y, amoeba_map, bacteria):
        # a cell is on the periphery if it borders (orthogonally) a 
        # cell that is not occupied by the amoeba
        out = []
        if (x, y) not in bacteria:
            if amoeba_map[x][(y - 1) % 100] == 0:
                out.append((x, (y - 1) % 100))
            if amoeba_map[x][(y + 1) % 100] == 0:
                out.append((x, (y + 1) % 100))
            if amoeba_map[(x - 1) % 100][y] == 0:
                out.append(((x - 1) % 100, y))
            if amoeba_map[(x + 1) % 100][y] == 0:
                out.append(((x + 1) % 100, y))

        return out
    
    # Find shape given size of anoemba, in the form of a list of offsets from center
    def get_desired_shape(self, shape=5):        
        if shape == 0:
            offsets = {(0,0), (0,1), (0,-1), (1,1), (1,-1)}
            total_cells = self.current_size-5
            i = 1
            j = 2
            while total_cells > 0:
                if j == 51:
                    n = math.ceil(math.sqrt(total_cells))
                    x = -1
                    if n % 2 == 0:
                        n+=1
                    # print(n, (n-1)/2)
                    while total_cells > 0:
                        if (x, 0) not in offsets:
                            offsets.add((x, 0))
                            total_cells -= 1
                        if total_cells > 0:
                            for i in range(int((n-1)/2)):
                                if total_cells > 1:
                                    if (x, i) not in offsets:
                                        offsets.add((x, i))
                                        total_cells -=1
                                    if (x, -i) not in offsets:
                                        offsets.add((x, -i))
                                        total_cells -=1
                                else:
                                    if (x, i) not in offsets:
                                        offsets.add((x, i))
                                        total_cells -=1
                        x-=1
                elif total_cells < 6:
                    if total_cells > 1:
                        # If possible add evenly
                        offsets.update({(i,j), (i,-j)})
                        total_cells-=2
                        i+=1
                    else:
                        # Add last remaining to left arm
                        offsets.update({(i, j)})
                        total_cells-=1
                else:
                    # if there are at least 6 add 3 to each side
                    offsets.update({(i, j), (i+1,j), (i+2, j), (i, -j), (i+1,-j), (i+2, -j)})
                    total_cells -= 6
                    i+=2
                    j+=1
        elif shape == 1:
            offsets = {(0,0), (0,1), (0,-1), (1,1), (1,-1)}
            total_cells = self.current_size-5
            j = 2
            step = 0
            while total_cells > 0:
                if step % 8 == 0:
                    offsets.add((1, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((1, -j))
                elif step % 8 == 1:
                    offsets.add((2, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((2, -j))
                elif step % 8 == 2:
                    offsets.add((3, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((3, -j))
                    j += 1
                elif step % 8 == 3:
                    offsets.add((1, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((1, -j))
                elif step % 8 == 4 or step % 8 == 5:
                    offsets.add((0, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((0, -j))
                    j += 1
                elif step % 8 == 6:
                    offsets.add((0, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((0, -j))
                elif step % 8 == 7:
                    offsets.add((1, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((1, -j))
                    j += 1

                step += 1
                total_cells-=1

        elif shape == 2:
            j = 2
            step = 0
            offsets = {(0,0), (0,1), (0,-1), (1,1), (1,-1)}
            total_cells = self.current_size-5
            while total_cells > 0:
                if step % 14 == 0:
                    offsets.add((1, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((1, -j))
                elif step % 14 == 1:
                    offsets.add((2, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((2, -j))
                elif step % 14 == 2:
                    offsets.add((3, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((3, -j))
                    j += 1
                elif step % 14 == 3:
                    offsets.add((3, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((3, -j))
                elif step % 14 == 4:
                    offsets.add((4, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((4, -j))
                elif step % 14 == 5:
                    offsets.add((5, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((5, -j))
                    j+=1
                elif step % 14 == 6:
                    offsets.add((3, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((3, -j))
                elif step % 14 == 7:
                    offsets.add((2, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((2, -j))
                elif step % 14 == 8:
                    offsets.add((1, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((1, -j))
                    j+=1
                elif step % 14 == 9:
                    offsets.add((1, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((1, -j))
                elif step % 14 == 10:
                    offsets.add((0, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((0, -j))
                    j+=1
                elif step % 14 == 11:
                    offsets.add((0, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((0, -j))
                    j+=1
                elif step % 14 == 12:
                    offsets.add((0, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((0, -j))
                elif step % 14 == 13:
                    offsets.add((1, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((1, -j))
                    j+=1
                total_cells -= 1
                step += 1

        # Not sure if correct, 5 wide tooth gap with 3 units of offset
        elif shape == 3:
            offsets = {(0,0), (0,1), (0,-1), (1,1), (1,-1)}
            total_cells = self.current_size-5
            j = 2
            i = 1
            step = 0
            while total_cells > 0:
                ###################### Add 3 long arm
                if step % 11 == 0:
                    offsets.add((i, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((i, -j))
                elif step % 11 == 1:
                    offsets.add((i+1, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((i+1, -j))
                elif step % 11 == 2:
                    offsets.add((i+2, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((i+2, -j))
                ######################
                ###################### Add 3 long offset arm
                elif step % 11 == 3:
                    offsets.add((i-1, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((i-1, -j))
                elif step % 11 == 4:
                    offsets.add((i-2, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((i-2, -j))
                elif step % 11 == 5:
                    offsets.add((i-3, j))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((i-3, -j))
                ######################
                ###################### Recreate inital offsets at new positions
                elif step % 11 == 6:
                    offsets.add((i-3, j+1))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((i-3, -(j+1)))
                elif step % 11 == 7:
                    offsets.add((i-4, j+1))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((i-4, -(j+1)))
                elif step % 11 == 8:
                    offsets.add((i-4, j+2))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((i-4, -(j+2)))
                elif step % 11 == 9:
                    offsets.add((i-4, j+3))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((i-4, -(j+3)))
                elif step % 11 == 10:
                    offsets.add((i-3, j+3))
                    total_cells-=1
                    if total_cells > 0:
                        offsets.add((i-3, -(j+3)))
                ######################
                    # Last step increment x and y with new position to grow from
                    j = j+4
                    i = i-3

                step += 1
                total_cells-=1
        
        elif shape == 4:
            # cur_size = self.current_size
            # eleven_wide_center = [[0,0], [1,0], [-1,0], [1,1], [-1,1], [2,1], [-2,1], [2,2], [-2,2], [2,3], [-2,3], [3,3], [-3,3], [3,4], [-3,4], [3,5], [-3,5], [4,5], [-4,5], [4,6], [-4,6], [4,7], [-4,7], [5,7], [-5,7], [5,8], [-5,8], [5,9], [-5,9], [6,9], [-6,9], [6,10], [-6,10], [6,11], [-6,11]]
            # eleven_wide_bottom = [[0,0], [0,-1], [0,-2], [1,-2], [1,-3], [1,-4], [2,-4], [2,-5], [2,-6], [3,-6], [3,-7], [3,-8], [4,-8], [4,-9], [4,-10], [5,-10], [5,-11], [6,-11], [7,-11], [7,-10], [8,-10], [8,-9], [8,-8], [9,-8], [9,-7], [9,-6], [10,-6], [10,-5], [10,-4], [11,-4], [11,-3], [11,-2], [12,-2], [12,-1], [12,0]]
            # eleven_wide_top    = [[-12, 0], [-12, -1], [-12, -2], [-11, -2], [-11, -3], [-11, -4], [-10, -4], [-10, -5], [-10, -6], [-9, -6], [-9, -7], [-9, -8], [-8, -8], [-8, -9], [-8, -10], [-7, -10], [-7, -11], [-6, -11], [-5, -11], [-5, -10], [-4, -10], [-4, -9], [-4, -8], [-3, -8], [-3, -7], [-3, -6], [-2, -6], [-2, -5], [-2, -4], [-1, -4], [-1, -3], [-1, -2], [0, -2], [0, -1], [0, 0]]

            # offsets = eleven_wide_center[:cur_size]
            # cur_size -= len(offsets)

            # while cur_size > len(offsets):
            #     temp = []
            #     temp.extend(eleven_wide_top[:(cur_size)//2])
            #     temp.extend(eleven_wide_bottom[:(cur_size + 1)//2])
            #     offsets.extend(temp)
            
            # offsets = set(offsets)

            cur_size = self.current_size
            eleven_wide_center = [[0,0], [1,0], [-1,0], [1,1], [-1,1], [2,1], [-2,1], [2,2], [-2,2], [2,3], [-2,3], [3,3], [-3,3], [3,4], [-3,4], [3,5], [-3,5], [4,5], [-4,5], [4,6], [-4,6], [4,7], [-4,7], [5,7], [-5,7], [5,8], [-5,8], [5,9], [-5,9], [6,9], [-6,9], [6,10], [-6,10], [6,11], [-6,11]]
            eleven_wide_bottom = np.array([[0,0], [0,-1], [0,-2], [1,-2], [1,-3], [1,-4], [2,-4], [2,-5], [2,-6], [3,-6], [3,-7], [3,-8], [4,-8], [4,-9], [4,-10], [5,-10], [5,-11], [6,-11], [7,-11], [7,-10], [8,-10], [8,-9], [8,-8], [9,-8], [9,-7], [9,-6], [10,-6], [10,-5], [10,-4], [11,-4], [11,-3], [11,-2], [12,-2], [12,-1], [12,0]])
            eleven_wide_top    = np.array([[0, 0], [0, -1], [0, -2], [-1, -2], [-1, -3], [-1, -4], [-2, -4], [-2, -5], [-2, -6], [-3, -6], [-3, -7], [-3, -8], [-4, -8], [-4, -9], [-4, -10], [-5, -10], [-5, -11], [-6, -11], [-7, -11], [-7, -10], [-8, -10], [-8, -9], [-8, -8], [-9, -8], [-9, -7], [-9, -6], [-10, -6], [-10, -5], [-10, -4], [-11, -4], [-11, -3], [-11, -2], [-12, -2], [-12, -1], [-12, 0]])

            offsets = eleven_wide_center[:cur_size]


            while cur_size > len(offsets):
                temp = []
                center_offset_bottom = np.array([6, 8]) + (np.array([12, -3]) * int(((len(offsets) / 35) - 1) / 2))
                bottom = eleven_wide_bottom[:(cur_size - len(offsets) + 1)//2] + center_offset_bottom
                temp.extend(bottom)

                center_offset_top = center_offset_bottom
                center_offset_top[0] *= -1
                top = eleven_wide_top[:(cur_size - len(offsets))//2] + center_offset_top
                temp.extend(top)

                offsets.extend(temp)

            offsets = set([(cord[1], cord[0]) for cord in list(offsets)])

        elif shape == 5:
            # new_v_center = [[0,0], [0,1], [0,-1], [1,1], [1,-1], [1,2], [1,-2], [2,2], [2,-2], [3,2], [3,-2], [3,3], [3,-3], [4,3], [4,-3], [5,3], [5,-3], [5,4], [5,-4], [5,5], [5,-5], [5,6], [5,-6]]

            new_v_center = [[0,0], [0,1], [0,-1], [1,1], [1,-1], [1,2], [1,-2], [2,2], [2,-2], [3,2], [3,-2], [3,3], [3,-3], [4,3], [4,-3], [5,3], [5,-3], [5,4], [5,-4], [6,4], [6,-4], [7,4], [7,-4]]
            new_v_top = [[0,0], [0,1], [1,1], [1,2], [2,2], [3,2], [3,3], [4,3], [5,3], [5,4], [6,4], [7,4]]
            new_v_bottom = [[0,0], [0,-1], [1,-1], [1,-2], [2,-2], [3,-2], [3,-3], [4,-3], [5,-3], [5,-4], [6,-4], [7,-4]]

            v_stor_center = [[0,0], [0,1], [0,-1], [1,2], [1,-2], [3,3], [3,-3], [5,4], [5,-4]]
            v_stor_top = [[0,0], [0,1], [1,2], [3,3], [5,4]]
            v_stor_bottom = [[0,0], [0,-1], [1,-2], [3,-3], [5,-4]]

            cur_size = self.current_size

            offsets = new_v_center[:cur_size]

            while min(239, cur_size) > len(offsets):
                top_offset = np.array([6,5]) * (int((len(offsets) - len(new_v_center)) / (len(new_v_center) + 1)) + 1)
                bottom_offset = np.array([6,-5]) * (int((len(offsets) - len(new_v_center)) / (len(new_v_center) + 1)) + 1)

                top = []

                if (cur_size - len(offsets))//2 > 0:
                    top = new_v_top[:(cur_size - len(offsets))//2] + top_offset
                bottom = new_v_bottom[:(cur_size - len(offsets) + 1)//2] + bottom_offset

                offsets.extend(top)
                offsets.extend(bottom)

            storage_size = cur_size - 239
            storage_offsets = []
            layer = 1
            displacement = 0

            while storage_size - len(storage_offsets) > 0:
                if displacement == 0:
                    storage_offsets.extend(list(v_stor_center[:storage_size] + np.array([-1 * layer, 0])))
                    displacement += 1
                    continue

                top_offset = (np.array([6,5]) * displacement) + [-1 * layer, 0]
                bottom_offset = (np.array([6,-5]) * displacement) + [-1 * layer, 0]

                if top_offset[1] >= 50:
                    layer += 1
                    displacement = 0
                    continue

                displacement += 1

                top_stor = []

                if (storage_size - len(storage_offsets))//2 > 0:
                    top_stor = v_stor_top[:(storage_size - len(storage_offsets))//2] + top_offset
                bottom_stor = v_stor_bottom[:(storage_size - len(storage_offsets) + 1)//2] + bottom_offset

                storage_offsets.extend(top_stor)
                storage_offsets.extend(bottom_stor)

            if len(storage_offsets) > 0:
                offsets.extend(storage_offsets)

            offsets = set([(cord[0], cord[1]) for cord in list(offsets)])

        return offsets
    
    def map_to_coords(self, amoeba_map: npt.NDArray) -> set[Tuple[int, int]]:
        # borrowed from group 2
        return set(list(map(tuple, np.transpose(amoeba_map.nonzero()).tolist())))

    def offset_to_absolute(self, offsets:set[Tuple[int]], center_point:Tuple[int]) -> set[Tuple[int]]:
        absolute_cords = set()
        for offset in offsets:
            absolute_cords.add(((center_point[0] + offset[0]) % MAP_LENGTH, (center_point[1] + offset[1]) % MAP_LENGTH))
        
        return absolute_cords

    def morph(self, offsets:set, center_point:Tuple[int]):
        # adapted from group 2
        cur_ameoba_points = self.map_to_coords(self.amoeba_map)
        desired_ameoba_points = self.offset_to_absolute(offsets, center_point)

        potential_retracts = list(self.periphery.intersection((cur_ameoba_points.difference(desired_ameoba_points))))
        potential_extends = list(self.movable_cells.intersection(desired_ameoba_points.difference(cur_ameoba_points)))

        # Loop through potential extends, searching for a matching retract
        retracts = []
        extends = []
        for potential_extend in [p for p in potential_extends]:
            # Ensure we only move as much as possible given our current metabolism
            if len(extends) >= self.num_available_moves:
                break

            matching_retracts = list(potential_retracts)
            matching_retracts.sort(key=lambda p: math.dist(p, potential_extend))

            for i in range(len(matching_retracts)):
                retract = matching_retracts[i]
                # Matching retract found, add the extend and retract to our lists
                if self.check_move(retracts + [retract], extends + [potential_extend]):
                    retracts.append(retract)
                    potential_retracts.remove(retract)
                    extends.append(potential_extend)
                    potential_extends.remove(potential_extend)
                    break
        
        return retracts, extends
    
    def reset_center(self, info_first_bit, new_coord): 
        if info_first_bit == "0":
            return [new_coord, 50]
        elif info_first_bit == "1":
            return [50, new_coord]

    def move(self, last_percept, current_percept, info) -> (list, list, int):
        """Function which retrieves the current state of the amoeba map and returns an amoeba movement

            Args:
                last_percept (AmoebaState): contains state information after the previous move
                current_percept(AmoebaState): contains current state information
                info (int): byte (ranging from 0 to 256) to convey information from previous turn
            Returns:
                Tuple[List[Tuple[int, int]], List[Tuple[int, int]], int]: This function returns three variables:
                    1. A list of cells on the periphery that the amoeba retracts
                    2. A list of positions the retracted cells have moved to
                    3. A byte of information (values range from 0 to 255) that the amoeba can use
        """
        self.turn += 1

        self.current_size = current_percept.current_size
        self.amoeba_map = current_percept.amoeba_map
        self.periphery = set(current_percept.periphery)
        self.bacteria = current_percept.bacteria
        self.movable_cells = set(current_percept.movable_cells)
        self.num_available_moves = int(np.ceil(self.metabolism * self.current_size))
        goal_percentage = self.current_size/self.goal_size
        bacteria_eaten = self.current_size-self.goal_size/4
        average_size =math.ceil((self.current_size+self.goal_size/4)/2)
        average_mouth = min(math.ceil((average_size-5)/3)+1, 100)
        
        ### PARSE INFO BYTE ###
        info_bin = format(info, '08b')
        info_first_bit = info_bin[0]    # first bit of the info byte
        info_L7_bits = info_bin[1:]     # last 7 bits of the info byte
        info_L7_int = int(info_L7_bits, 2)  # info_L7_int holds int value of last 7 bits (stores coordinate)


        ### GET DESIRED OFFSETS FOR CURRENT MORPH ###
        desired_shape_offsets = self.get_desired_shape(5)

        ### INCREMENT CENTER POINT PHASE ###
        # move amoeba: x_cord is info_L7_int because initial info_L7_int val is 0, indicating initialization/building phase
        init_phase = info_L7_int == 0
        x_cord = info_L7_int - 1

        # determine if density suggests flip is adventagous
        total_distance = 0
        if x_cord <= 50:
            total_distance = 50+x_cord
        else:
            total_distance = x_cord-50

        current_density_est = bacteria_eaten/(average_mouth*total_distance)

        '''
        # not working solution #1 
        if x_cord == 50 and current_density_est < LOW_DENSITY:
            info_first_bit = "1"
        elif x_cord == 49 and info_first_bit == "1":
            info_first_bit = "0"
        '''

        '''
        # not working solution #2
        if x_cord == 50 and info_first_bit == "0" and current_density_est < LOW_DENSITY and (self.current_size < self.goal_size / 3):
            info_first_bit = "1"
        elif x_cord == 50 and info_first_bit == "1" and (self.current_size > self.goal_size / 3 and self.current_size < self.goal_size * 2 / 3):
            info_first_bit = "0"
        elif x_cord == 50 and info_first_bit == "0" and (self.current_size > self.goal_size * 2 / 3):
            info_first_bit = "1"
        '''

            
        # if first but is flipped, flip the desired shape to (y, x)
        if int(info_first_bit) == 1:
            desired_shape_offsets = [tuple(reversed(offset)) for offset in desired_shape_offsets]

        # move under these 2 conditions
        # 1: end of initialization phase
        new_center = self.reset_center(info_first_bit, x_cord)
        if init_phase:
            x_cord = 50

            new_center = self.reset_center(info_first_bit, x_cord)
            if self.in_formation(desired_shape_offsets, new_center):
                init_phase = False
                x_cord = 51
                new_center = self.reset_center(info_first_bit, x_cord)

        # 2: not in initialization phase, and in formation
        elif self.in_formation(desired_shape_offsets, new_center, err=0.2):
            x_cord += 1
            x_cord %= 100


        ### MORPH PHASE ###
        center_point = self.reset_center(info_first_bit, x_cord)
        retracts, moves = self.morph(desired_shape_offsets, center_point)

        # catch error (if moves == 0, no move was made, so we should step back until we can move)
        if len(moves) == 0:
            while len(moves) == 0:
                x_cord = ((x_cord + 100) - 1) % 100
                center_point = self.reset_center(info_first_bit, x_cord)
                retracts, moves = self.morph(desired_shape_offsets, center_point)
            x_cord = ((x_cord + 100) - 1) % 100


        ### INFO BYTE ###
        # first bit == nothing right now
        # 0 == initialization
        # 1 - 100 => 0 - 99 == x_cord
        if init_phase:
            info_L7_bits = format(0, '07b')
        else:
            info_L7_bits = format(x_cord + 1, '07b')
        
        info_bin = info_first_bit + info_L7_bits
        info = int(info_bin, 2)

        return retracts, moves, info
    

    def in_formation(self, desired_shape_offsets, cur_center, err=0.0) -> bool:
        cur_ameoba_points = self.map_to_coords(self.amoeba_map)
        desired_ameoba_points = self.offset_to_absolute(desired_shape_offsets, cur_center)

        num_potential_retracts = len(self.periphery.intersection((cur_ameoba_points.difference(desired_ameoba_points))))
        num_total_periphery = len(cur_ameoba_points)

        return (num_potential_retracts / num_total_periphery) <= err
