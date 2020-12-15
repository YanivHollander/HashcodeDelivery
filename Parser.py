from Definitions import Product
from OrderInventory import Inventory, Order
from WarehouseCustomer import Warehouse, Customer
import unittest
from typing import List
import matplotlib.pyplot as plt

class Parser:
    def __init__(self, inputFilename, mapFilename = None):
        f = open(inputFilename)

        ## Header
        header = f.readline().split(' ')
        self.nRows      = int(header[0])
        self.nColumns   = int(header[1])
        self.nDrones    = int(header[2])
        self.nTurns     = int(header[3])
        self.maxPayload = int(header[4])

        ## Products
        nProducts = int(f.readline())   # FIXME: Make sure all product weights appear on the same line
        products = f.readline().split(' ')
        self.products = []
        for index, weight in enumerate(products):
            product = Product (index, int(weight))
            self.products.append(product)

        ## Warehouses
        nWarehouses = int(f.readline())
        self.warehouses = []
        for i in range(nWarehouses):
            location = f.readline().split(' ')
            inventory = f.readline().split(' ')
            warehouseInventory = Inventory()
            for j, quantity in enumerate(inventory):
                if int(quantity) != 0:
                    product = self.products[j]
                    warehouseInventory.append(product, int(quantity))
            self.warehouses.append(Warehouse((int(location[0]), int(location[1])), warehouseInventory, index = i))

        ## Orders
        self.nOrders = int(f.readline())
        self.customers: List[Customer] = []
        for i in range(self.nOrders):
            location = f.readline().split(' ')
            nItems = int(f.readline())
            items = f.readline().split(' ')
            customerOrder = Inventory()
            for item in items:
                products = [prod for prod in self.products if prod.index == int(item)]
                if len(products) == 0:
                    raise RuntimeError("Item to add to order cannot be found in product list")
                customerOrder.append(products[0], 1)
            self.customers.append(Customer((int(location[0]), int(location[1])), customerOrder, index = i))
        f.close()

        # Outputing a map
        if mapFilename is not None:
            self.__outputMap(mapFilename)

    def __repr__(self):
        return repr((self.nRows, self.nColumns, self.nDrones, self.nTurns, self.maxPayload, self.products,
                     self.warehouses, self.customers))

    def __str__ (self):
        products = ""
        for product in (self.products):
            products += str(product) + '\n'
        warehouses = ""
        for warehouse in (self.warehouses):
            warehouses += str(warehouse) + '\n'
        customers = ""
        for customer in (self.customers):
            customers += str(customer) + '\n'
        return ('Parameters' + '\n'
                '==========' + '\n'
                'Number of rows = ' + str(self.nRows) + ', number of columns = ' + str(self.nColumns) + '\n'
                'Number of drones = ' + str(self.nDrones) + ', maximal drone payload = ' + str(self.maxPayload) + '\n'
                'Products\n' + '--------\n' + products +
                'Warehouses\n' + '----------\n' + warehouses +
                'Customers\n' + '---------\n' + customers)

    def __outputMap(self, mapFilename):
        x = []
        y = []
        for customer in self.customers:
            x.append(customer.location()[0])
            y.append(customer.location()[1])
        plt.scatter(x, y)
        x.clear()
        y.clear()
        for warehouse in self.warehouses:
            x.append(warehouse.location()[0])
            y.append(warehouse.location()[1])
        plt.scatter(x, y, marker='x')
        plt.savefig(mapFilename)

class TestParser(unittest.TestCase):
    def setUp(self):
        self.params = Parser('SmallInput.dat')

    def test_parsing(self):
        print(self.params)

if __name__ == '__main__':
    unittest.main()
