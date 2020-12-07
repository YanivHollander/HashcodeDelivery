from typing import List, Tuple
import unittest
import numpy as np
from scipy.spatial import distance as dst

class Product:
    def __init__(self, index, weight):
        self.index = index      # Product distinctive index
        self.weight = weight    # Product weight

    def __repr__(self):
        return {"index": self.index, 'weight': self.weight}

    def __str__(self):
        return "index = " + str(self.index) + ", weight = " + str(self.weight)

Products = List[Product]

Location = Tuple[int, int]

def distance(orig: Location, dest: Location) -> int:
    """
    Calculates the Euclidean distance between two locations, ceiled to integer
    :param dest: Destination in [c, r]
    :return: Distance in number of turns (Euclidean rounded up to nearest integer)
    """
    return np.ceil(dst.euclidean(orig, dest))

class TestDefinition(unittest.TestCase):
    def setUp(self):
        pass

    def test_append_to_inventory (self):
        pass

if __name__ == '__main__':
    unittest.main()

