from Definitions import Product, Location
from OrderInventory import Inventory, Order

class Node:
    def __init__(self, location: Location = (0, 0), order: Inventory = None, index = -1):
        if order is None:
            order = Inventory()
        self._location = location
        self._order = order
        self._booked = Order ()
        self.__index = index

    def __repr__(self):
        return repr(self.__index)

    def __str__(self):
        return "location: " + str(self._location) + ", order/inventory: " + str(self._order)

    ## __eq__ and __hash__ based on index, for using class as a hashing key
    def __eq__(self, other):
        return self.__index == other.__index

    def __hash__(self):
        return hash(self.__index)

    def order(self):        # FIXME: Check if return by reference of by value
        return self._order

    def index(self) -> int:
        return self.__index

    def location(self) -> Location:
        return self._location

    def _checkProducts(self, product: Product, nToLoad: int) -> None:
        """
        Check that a specific product exists n times in the inventory
        :param product:
        :param nToLoad:
        :return:
        """
        raise NotImplementedError("Check products should be called for a specified Node (customer or warehouse)")

    def remove(self, product: Product, nToRemove: int, considerBooking = False) -> None:
        """
        Remove items from inventory (warehouse)/order (customer)
        :param product:
        :param nToRemove:
        :param considerBooking:
        :return:
        """
        self._checkProducts(product, nToRemove)
        if considerBooking:
            if product not in self._booked:
                raise RuntimeError("Product to be removed from node (warehouse/customer) has not been booked in "
                                   "advance")
            if self._booked[product] < nToRemove:
                raise RuntimeError("Trying to remove more products from node (warehouse/customer) than were booked in "
                                   "advance")
            self._booked[product] -= nToRemove
            if self._booked[product] == 0:
                del self._booked[product]
        self._order.remove(product, nToRemove)

    def book(self, orderToBook: Inventory):

        # Check that booked order exists in invetory
        orderToBookMinusExistingBooking = self.createAvailableOrder(orderToBook)
        for product in orderToBookMinusExistingBooking:
            self._checkProducts(product, orderToBookMinusExistingBooking[product])

        # Append order to warehouse book
        for product in orderToBookMinusExistingBooking:
            if product not in self._booked:
                self._booked[product] = 0
            self._booked[product] += orderToBookMinusExistingBooking[product]

    def unbook(self, orderToUnbook: Inventory):
        for product in orderToUnbook:
            if product not in self._booked:
                raise RuntimeError("Cannot unbook product " + str(product) + ". It is not booked")
            if self._booked[product] < orderToUnbook[product]:
                raise RuntimeError("Tyring to unbook more prudcts than there are in the booking, for product: " +
                                   str(product))
            self._booked[product] -= orderToUnbook[product]
            if self._booked[product] == 0:
                del self._booked[product]

    def clearBook(self):
        self._booked.clear()

    def getProductsMinusBookings(self) -> Inventory:
        """
        Get products in the warehouse inverntory/customer order after deducting the current booking
        :return: Order of warehouse available products/order available for customer
        """
        ret = Inventory()
        for product in self._order:
            ret.append(product, self._order[product])
            if product in self._booked:
                ret.remove(product, self._booked[product])
        return ret

    def createAvailableOrder(self, order: Inventory) -> Inventory:
        """
        For a given input order output products that are available in te warehouse/customer (booking considered)
        :param order: An input required order
        :return: An output order of products from the input order that are available in the warehouse/customer
        """
        availableInventory = self.getProductsMinusBookings()
        availableOrder = Inventory()
        for product in order:
            if product in availableInventory.products():
                availableOrder.append(product, min(order[product], availableInventory[product]))
        return availableOrder

class Warehouse(Node):
    def __init__(self, location: Location = (0, 0), order: Inventory = None, index = -1):
        super().__init__(location, order, index)

    def _checkProducts(self, product: Product, nToLoad: int) -> None:
        if not self._order.exist(product):
            raise RuntimeError("Product " + str(product) + " does not exist in warehouse inventory")
        if nToLoad > self._order.count(product):
            raise RuntimeError("Warehouse does not have " + str(nToLoad) + " items of product: " + str(product))

class Customer(Node):
    def __init__(self, location: Location = (0, 0), order: Inventory = None, index = -1):
        super().__init__(location, order, index)

    def _checkProducts(self, product: Product, nToDeliver: int) -> None:
        if not self._order.exist(product):
            raise RuntimeError("Product " + str(product) + " is not part of customer order")
        if nToDeliver > self._order.count(product):
            raise RuntimeError("Customer " + str(self.__index) + " only needs " + str(self._order.count(product)) +
                               " items of product (" + str(product) + "). Trying to deliver him " + str(nToDeliver) +
                               " items")

    def isComplete(self, considerBooking = False) -> bool:
        if considerBooking:
            return self.getProductsMinusBookings().empty()
        return self._order.empty()

