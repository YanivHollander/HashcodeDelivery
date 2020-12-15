from Definitions import Product
import unittest
from typing import Dict

class Order(object):
    def __init__(self):
        self._products: Dict[Product, int] = {}  # Dictionary for frequency of each product

    def __repr__(self):
        return repr((self._products))

    def __str__(self):
        ret = "Order: "
        for product in self._products:
            ret += " (" + str(product) + "): " + str(self._products[product]) + "|"
        return ret

    def __iter__(self):
        return iter(self._products)

    def __getitem__(self, product: Product):
        return self._products[product]

    def __setitem__(self, product: Product, n: int):
        self._products[product] = n

    def __delitem__(self, product: Product):
        del self._products[product]

    def products(self) -> Dict[Product, int]:
        return self._products

    def clear(self) -> None:
        self._products.clear()

    def append(self, product: Product, n: int) -> None:
        if n < 0:
            raise RuntimeError ("Trying to append a negative number of items of product " + str(product))
        if product in self._products:
            self._products[product] += n
        else:
            self._products[product] = n

    def remove(self, product: Product, n: int) -> None:
        if product in self._products and self._products [product] >= n:
            self._products [product] -= n
        else:
            raise RuntimeError ("Trying to remove more products " + str(product) + " than exist")
        if self._products [product] == 0:
            del self._products [product]

    def count(self, product: Product) -> int:
        if self.exist(product):
            return self._products[product]
        return 0

    def empty(self) -> bool:
        if self._products:
            return False
        return True

    def exist(self, product: Product) -> bool:
        return product in self._products

class Inventory(Order):
    def __init__(self):
        super().__init__()
        self.__weight = 0

    def __repr__(self):
        return repr((self._products, self.__weight))

    def __str__(self):
        ret = "Inventory: "
        for product in self._products:
            ret += " (" + str(product) + "): " + str(self._products [product]) + "|"
        ret += " total weight = " + str(self.__weight)
        return ret

    def clear (self) -> None:
        super().clear()
        self.__weight = 0

    def append (self, product: Product, n: int) -> None:
        super().append(product, n)
        self.__weight += product.weight * n

    def remove (self, product: Product, n: int) -> None:
        super().remove(product, n)
        self.__weight -= product.weight * n

    def weight (self) -> int:
        return self.__weight

class TestOrderInventory(unittest.TestCase):
    def setUp(self):
        self.inventory = Inventory()

    def test_append_to_inventory(self):
        product0 = Product(0, 5)
        product1 = Product(2, 3)
        self.inventory.clear()
        self.inventory.append(product0, 3)
        self.inventory.append(product1, 1)
        print(self.inventory)
        self.assertEqual(product0.weight * 3 + product1.weight * 1, self.inventory.weight())

if __name__ == '__main__':
    unittest.main()
