from Definitions import Product
from OrderInventory import Inventory, Order

class Warehouse:
    def __init__(self, location = (0, 0), inventory: Inventory = None, index = -1):
        if inventory is None:
            inventory = Inventory()
        self.location = location
        self.inventory = inventory
        self.__booked: Order = {}
        self.__index = index

    def __repr__(self):
        return {'location': self.location, 'inventory': self.inventory}

    def __str__(self):
        return "location: " + str(self.location) + ", " + str(self.inventory)

    def checkInvenroty (self, product: Product, nToLoad: int) -> None:
        if not self.inventory.exist(product):
            raise RuntimeError("Product " + str(product) + " does not exist in warehouse inventory")
        if nToLoad > self.inventory.count(product):
            raise RuntimeError("Warehouse does not have " + str(nToLoad) + " items of product: " + str(product))

    def remove (self, product: Product, nToRemove: int, considerBooking = False) -> None:
        self.checkInvenroty(product, nToRemove)
        if considerBooking:
            if product not in self.__booked:
                raise RuntimeError("Product to be removed from warehouse was not booked in advance")
            if self.__booked[product] < nToRemove:
                raise RuntimeError("Trying to remove more products fro mwarehouse than were booked in advance")
            self.__booked[product] -= nToRemove
            if self.__booked[product] == 0:
                del self.__booked[product]
        self.inventory.remove(product, nToRemove)

    def book(self, orderToBook: Order):

        # Check that booked order exists in invetory
        for product in orderToBook:
            self.checkInvenroty(product, orderToBook[product])

        # Append order to warehouse book
        for product in orderToBook:
            if product in self.__booked:
                self.__booked[product] += orderToBook[product]
            else:
                self.__booked[product] = orderToBook[product]

    def getInventoryMinusBookings(self) -> Order:
        ret = Order()
        for product in self.inventory:
            ret.append(product, self.inventory[product])
            if product in self.__booked:
                ret.remove(product, self.__booked[product])
        return ret

    def createAvailableOrder(self, order: Order) -> Order:
        availableInventory = self.getInventoryMinusBookings()
        availableOrder = Order()
        for product in order:
            if product in availableInventory:
                availableOrder.append(product, min(order[product], availableInventory[product]))
        return availableOrder

    def index(self) -> int:
        return self.__index

class Customer:
    def __init__(self, location = (0, 0), order: Order = None, index = -1):
        if order is None:
            order = Order()
        self.location = location
        self.order = order
        self.__index = index

    def __repr__(self):
        return {'location': self.location, 'order': self.order}

    def __str__(self):
        return "location: " + str(self.location) + ", " + str(self.order)

    def checkOrder (self, product: Product, nToDeliver: int) -> None:
        if not self.order.exist(product):
            raise RuntimeError("Product " + str(product) + " is not part of customer order")
        if nToDeliver > self.order.count(product):
            raise RuntimeError("Customer " + str(self.__index) + " only needs " + str(self.order.count(product)) +
                               " items of product (" + str(product) + "). Trying to deliver him " + str(nToDeliver) +
                               " items")

    def receive(self, product: Product, nToDeliver: int) -> None:
        self.checkOrder (product, nToDeliver)
        self.order.remove(product, nToDeliver)

    def index(self) -> int:
        return self.__index

    def isComplete(self) -> bool:
        return self.order.empty()
