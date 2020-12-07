from Definitions import Location, Product, distance
from OrderInventory import Inventory, Order
import unittest
from enum import Enum, auto

class DroneStatus(Enum):
    Idle = auto()
    Traveling = auto()
    Load = auto()
    Unload = auto()

class DroneTask:
    def __init__(self):
        self.status = DroneStatus.Idle  # Current status
        self.time = -1                  # Start time of current drone task
        self.duration = -1              # Duration of current task
        self.dest = (0, 0)              # Destination of current task
        self.products = Order()         # Dictionary for frequency of each product to load/unload in current task

    def setIdle(self):
        self.status = DroneStatus.Idle
        self.time = -1
        self.duration = -1
        self.products = Order()

    def setTravel(self, time: int, duration: int, dest: Location):
        self.status = DroneStatus.Traveling
        self.time = time
        self.duration = duration
        self.dest = dest
        self.products = Order()

    def setLoad(self, time: int, product: Product, nToLoad: int):
        self.status = DroneStatus.Load
        if self.time != -1 and self.time != time:
            raise RuntimeError("Since load duration is 1, cannot set loading at two different times")
        self.time = time
        self.duration = 1
        self.products.append(product, nToLoad)

    def setUnload(self, time: int, product: Product, nToUnoad: int):
        self.status = DroneStatus.Unload
        if self.time != -1 and self.time != time:
            raise RuntimeError("Since unload duration is 1, cannot set unloading at two different times")
        self.time = time
        self.duration = 1
        self.products.append(product, nToUnoad)

class Drone:
    def __init__(self, location0: Location, maxWeight: int, inventory: Inventory = None, index = -1):
        if inventory is None:
            inventory = Inventory()
        if inventory.weight() > maxWeight:
            raise RuntimeError("Drone is instantiated with a too heavy inventory")
        self.__location = location0
        self.__inventory = inventory
        self.maxWeight = maxWeight
        self.task = DroneTask()
        self.__droneTime = 0
        self.__index = index

    # def __repr__(self):
    #     return {'__location': self.__location, '__inventory': self.__inventory, 'maxWeight': self.maxWeight,
    #             'task': self.task, '__droneTime': self.__droneTime}

    def refreshDroneStatus(self, time: int) -> None:
        """
        Refreshes the status of the drone at a given time, based on its current operation
        :param time:    Current time
        :return:
        """
        if time < self.__droneTime:
            raise RuntimeError("Tyring to sample drone in past time to its current inner clock")
        self.__droneTime = time

        # Traveling mission complete
        if self.task.status == DroneStatus.Traveling and time >= self.task.time + self.task.duration:
            self.__location = self.task.dest
            self.task.setIdle()

        # Loading mission complete
        elif self.task.status == DroneStatus.Load and time >= self.task.time + self.task.duration:
            for product in self.task.products:
                self.__inventory.append(product, self.task.products[product])     # Append products to drone inventory
            self.task.setIdle()

        # Unloading mission complete
        elif self.task.status == DroneStatus.Unload and time >= self.task.time + self.task.duration:
            for product in self.task.products:
                self.__inventory.remove(product, self.task.products[product])     # Remove product from drone inventory
            self.task.setIdle()

    def status(self, time: int) -> DroneStatus:
        """
        Checks the status of the drone at a given time
        :param time:    Current time
        :return: idle or busy
        """
        self.refreshDroneStatus(time)
        return self.task.status

    def location(self, time: int) -> Location:
        """
        Get the location of the drone, at a given time
        :param time:    Current time
        :return: location
        """
        self.refreshDroneStatus(time)
        return self.__location

    def time(self) -> int:
        """
        Return drone inner clock
        :return: time
        """
        return self.__droneTime

    def inventory(self, time: int) -> Inventory:
        """
        Get the inventory of the drone, at a given time
        :param time:    Current time
        :return: inventory
        """
        self.refreshDroneStatus(time)
        return self.__inventory

    def index(self) -> int:
        return self.__index

    def travel(self, dest: Location, time: int) -> None:
        """
        Send the drone to a location
        :param dest:    Destination location
        :param time:    Time at travel start. During flight this function can be called with larger times, which will
                        not have side-effects to the current mission
        :return:
        """
        self.refreshDroneStatus(time)
        if self.task.status == DroneStatus.Idle:
            self.task.setTravel(time, distance(self.__location, dest), dest)
        elif self.task.status != DroneStatus.Traveling:
            raise RuntimeError("Cannot order a drone to travel if it is doing something else")
        elif self.task.dest != dest:
            raise RuntimeError("Cannot change drone destination during flight")
        self.refreshDroneStatus(time)

    def load(self, product: Product, nToLoad: int, time: int) -> None:
        """
        Load items of a product type
        :param product: Product type to load
        :param nToLoad: Number of product items to load
        :param time:    Time at loading start
        :return:
        """
        self.refreshDroneStatus(time)
        self.checkWeightLimit(product, nToLoad)    # Throw if trying to exceed drone capacity
        if self.task.status == DroneStatus.Idle or self.task.status == DroneStatus.Load:
            self.task.setLoad(time, product, nToLoad)
        elif self.task.status != DroneStatus.Load:
            raise RuntimeError("Cannot order a drone to load if it is doing something else")
        self.refreshDroneStatus(time)

    def unload(self, product: Product, nToUnload: int, time: int) -> None:
        """
        Unload items of a product type
        :param product:     Product type to unload
        :param nToUnload:   Number of product items to unload
        :param time:        Time at unloading start
        :return:
        """
        self.refreshDroneStatus(time)
        self.checkInventory(product, nToUnload)     # Throw if trying to unload more than what is in the inventory
        if self.task.status == DroneStatus.Idle or self.task.status == DroneStatus.Unload:
            self.task.setUnload(time, product, nToUnload)
        elif self.task.status != DroneStatus.Unload:
            raise RuntimeError("Cannot order a drone to unload if it is doing something else")
        self.refreshDroneStatus(time)

    def wait(self, time: int, duration: int):
        """
        Wait for a certain duration (drone is considered busy during waiting time)
        :param time:        Time at wait start
        :param duration:    Wait duration
        :return:
        """
        if time < 0:
            raise RuntimeError("Negative starting time")
        self.__timeBegin = time
        self.__timeEnd = time + duration

    def checkWeightLimit(self, product: Product, nToLoad: int) -> None:
        wTask = 0
        if self.task.status == DroneStatus.Load:
            for productTask in self.task.products:
                wTask += productTask.weight * self.task.products[productTask]
        if self.__inventory.weight () + wTask + product.weight * nToLoad > self.maxWeight:
            raise RuntimeError ("Cannot load product due to drone capacity weight limit")

    def checkInventory(self, product: Product, nToDeliver: int) -> None:
        if not self.__inventory.exist(product):
            raise RuntimeError("Product " + str(product) + " does not exist in drone inventory")
        nTask = 0
        if self.task.status == DroneStatus.Unload:
            if product in self.task.products:
                nTask = self.task.products[product]
        if nToDeliver + nTask > self.__inventory.count(product):
            raise RuntimeError("Drone does not have " + str(nToDeliver) + " items of product: " + str(product))

class TestDrone(unittest.TestCase):
    def setUp(self):
        self.drone = Drone ([0, 0], 15)

    def test_travel(self):
        pass

    def test_load(self):
        product0 = Product(0, 5)
        product1 = Product(2, 3)
        self.assertRaises(RuntimeError, self.drone.load, product0, 6, 0)      # Trying to load more than drone capacity
        self.drone.load(product0, 1, 0)        # Should be fine - not exceeding drone capacity
        self.drone.load(product1, 2, 1)        # Should be fine - not exceeding drone capacity

        self.drone.unload(product1, 2, 2)

    def test_unload(self):
        inventory = Inventory()
        product0 = Product(0, 5)
        product1 = Product(2, 3)
        inventory.append(product0, 1)
        inventory.append(product1, 3)
        self.drone = Drone([0, 0], 17, inventory = inventory)
        self.drone.unload(product1, 1, 1)
        self.assertEqual(self.drone.inventory(2).weight(), 11)
        self.drone.unload(product1, 1, 2)
        self.assertEqual(self.drone.inventory(3).weight(), 8)

        self.drone.unload(product1, 1, 3)
        self.drone.unload(product0, 1, 3)
        self.assertEqual(self.drone.inventory(4).weight(), 0)

if __name__ == '__main__':
    unittest.main()

