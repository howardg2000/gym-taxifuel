# import gym
# from gym import error, spaces, utils
# from gym.utils import seeding

import sys
from contextlib import closing
from io import StringIO
from gym import utils
from gym.envs.toy_text import discrete
import numpy as np

MAP = [
    "+---------+",
    "|R: |F: :G|",
    "| : | : : |",
    "| : : : : |",
    "| | : | : |",
    "|Y| : |B: |",
    "+---------+",
]


class TaxiFuelEnv(discrete.DiscreteEnv):
    """
    The Taxi Problem
    from "Hierarchical Reinforcement Learning with the MAXQ Value Function Decomposition"
    by Tom Dietterich

    Description:
    There are four designated locations in the grid world indicated by R(ed), G(reen), Y(ellow), and B(lue). When the episode starts, the taxi starts off at a random square with max fuel and the passenger is at a random location. The taxi drives to the passenger's location, picks up the passenger, drives to the passenger's destination (another one of the four specified locations), and then drops off the passenger. Each move consumes 1 fuel. Once the passenger is dropped off, the episode ends.

    Observations: 
    There are 5500 discrete states since there are 25 taxi positions, 5 possible locations of the passenger (including the case when the passenger is in the taxi), 4 destination locations, and 11 possible fuel states. 
    
    Passenger locations:
    - 0: R(ed)
    - 1: G(reen)
    - 2: Y(ellow)
    - 3: B(lue)
    - 4: in taxi
    
    Destinations:
    - 0: R(ed)
    - 1: G(reen)
    - 2: Y(ellow)
    - 3: B(lue)

    Fuel:
     - 0 to 10: start with 10
        
    Actions:
    There are 6 discrete deterministic actions:
    - 0: move south
    - 1: move north
    - 2: move east 
    - 3: move west 
    - 4: pickup passenger
    - 5: dropoff passenger
    - 6: refill fuel tank to 10
    
    Rewards: 
    There is a reward of -1 for each action and an additional reward of +20 for delivering the passenger. There is a reward of -10 for executing actions "pickup", "dropoff", "refill" illegally.
    

    Rendering:
    - blue: passenger
    - magenta: destination
    - yellow: empty taxi
    - green: full taxi
    - other letters (R, G, Y and B): locations for passengers and destinations
    

    state space is represented by:
        (taxi_row, taxi_col, passenger_location, destination, fuel)
    """
    metadata = {'render.modes': ['human', 'ansi']}

    def __init__(self):
        self.desc = np.asarray(MAP, dtype='c')

        self.locs = locs = [(0,0), (0,4), (4,0), (4,3)]
        self.fuel_station = fuel_station = (0,2)

        num_states = 5500
        num_rows = 5
        num_columns = 5
        max_fuel = 10
        max_row = num_rows - 1
        max_col = num_columns - 1
        initial_state_distrib = np.zeros(num_states)
        num_actions = 7
        P = {state: {action: []
                     for action in range(num_actions)} for state in range(num_states)}
        for row in range(num_rows):
            for col in range(num_columns):
                for pass_idx in range(len(locs) + 1):  # +1 for being inside taxi
                    for dest_idx in range(len(locs)):
                        for fuel in range(max_fuel + 1):  # +1 for 0 fuel
                            state = self.encode(row, col, pass_idx, dest_idx, fuel)
                            if pass_idx < 4 and pass_idx != dest_idx and fuel == max_fuel:
                                initial_state_distrib[state] += 1
                            for action in range(num_actions):
                                # defaults
                                new_row, new_col, new_pass_idx, new_fuel = row, col, pass_idx, fuel
                                reward = -1 # default reward when there is no pickup/dropoff/refill
                                done = False
                                taxi_loc = (row, col)

                                moved = False # indicates if fuel is consumed

                                if action == 0: # south
                                    new_row = min(row + 1, max_row)
                                    if row != max_row:
                                        moved = True
                                elif action == 1: # north
                                    new_row = max(row - 1, 0)
                                    if row != 0:
                                        moved = True
                                if action == 2 and self.desc[1 + row, 2 * col + 2] == b":": # east, no wall
                                    new_col = min(col + 1, max_col)
                                    if col != max_col:
                                        moved = True
                                elif action == 3 and self.desc[1 + row, 2 * col] == b":": # west, no wall
                                    new_col = max(col - 1, 0)
                                    if col != 0:    
                                        moved = True
                                elif action == 4:  # pickup
                                    if (pass_idx < 4 and taxi_loc == locs[pass_idx]):
                                        new_pass_idx = 4
                                    else: # passenger not at location
                                        reward = -10
                                elif action == 5:  # dropoff
                                    if (taxi_loc == locs[dest_idx]) and pass_idx == 4:
                                        new_pass_idx = dest_idx
                                        done = True
                                        reward = 20
                                    elif (taxi_loc in locs) and pass_idx == 4:
                                        new_pass_idx = locs.index(taxi_loc)
                                    else: # dropoff at wrong location
                                        reward = -10
                                elif action == 6: # refill
                                    if (taxi_loc == fuel_station):
                                        new_fuel = 10
                                    else: # not at fuel station
                                        reward = -10
                                if moved:
                                    if fuel == 0:
                                        reward = -10
                                    new_fuel = max(0, fuel - 1)

                                new_state = self.encode(
                                    new_row, new_col, new_pass_idx, dest_idx, new_fuel)
                                P[state][action].append(
                                    (1.0, new_state, reward, done))
        initial_state_distrib /= initial_state_distrib.sum()
        discrete.DiscreteEnv.__init__(
            self, num_states, num_actions, P, initial_state_distrib)

    def encode(self, taxi_row, taxi_col, pass_loc, dest_idx, fuel):
        # (5) 5, 5, 4, 11
        i = taxi_row
        i *= 5
        i += taxi_col
        i *= 5
        i += pass_loc
        i *= 4
        i += dest_idx
        i *= 11
        i += fuel
        return i

    def decode(self, i):
        out = []
        out.append(i % 11)
        i = i // 11
        out.append(i % 4)
        i = i // 4
        out.append(i % 5)
        i = i // 5
        out.append(i % 5)
        i = i // 5
        out.append(i)
        assert 0 <= i < 5
        return reversed(out)

    def render(self, mode='human'):
        outfile = StringIO() if mode == 'ansi' else sys.stdout

        out = self.desc.copy().tolist()
        out = [[c.decode('utf-8') for c in line] for line in out]
        taxi_row, taxi_col, pass_idx, dest_idx, fuel = self.decode(self.s)

        def ul(x): return "_" if x == " " else x
        if pass_idx < 4:
            out[1 + taxi_row][2 * taxi_col + 1] = utils.colorize(
                out[1 + taxi_row][2 * taxi_col + 1], 'yellow', highlight=True)
            pi, pj = self.locs[pass_idx]
            out[1 + pi][2 * pj + 1] = utils.colorize(out[1 + pi][2 * pj + 1], 'blue', bold=True)
        else:  # passenger in taxi
            out[1 + taxi_row][2 * taxi_col + 1] = utils.colorize(
                ul(out[1 + taxi_row][2 * taxi_col + 1]), 'green', highlight=True)

        di, dj = self.locs[dest_idx]
        out[1 + di][2 * dj + 1] = utils.colorize(out[1 + di][2 * dj + 1], 'magenta')
        outfile.write("\n".join(["".join(row) for row in out]) + "\n")
        if self.lastaction is not None:
            outfile.write("  ({})\n".format(["South", "North", "East", "West", "Pickup", "Dropoff", "Refill"][self.lastaction]))
        else: outfile.write("\n")

        # No need to return anything for human
        if mode != 'human':
            with closing(outfile):
                return outfile.getvalue()
