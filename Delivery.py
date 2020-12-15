from Drone import Drone, DroneStatus
import unittest
from Definitions import Product, Location
from OrderInventory import Inventory, Order
from WarehouseCustomer import Warehouse, Customer
import numpy as np
from enum import Enum, auto
from typing import Dict, List

class MissionType(Enum):
    Load = auto()
    Deliver = auto()
    Wait = auto()
    Unload = auto()
    LoadAndDeliver = auto()

class Mission:
    def __init__(self, missionType: MissionType, time: int, order: Order,
                 warehouse: Warehouse = None, customer: Customer = None):
        if warehouse is None:
            warehouse = Warehouse()
        if customer is None:
            customer = Customer()
        self.missionType = missionType
        self.time = time
        self.order = order
        self.warehouse = warehouse
        self.customer = customer
        self.travelPhase = False
        self.loadUnloadPhase = False
        self.loadPhase = True           # Used in combo loading-delver mission

class Delivery:
    def __init__(self):
        self.__mission: Dict[Drone, Mission] = {}   # Mission controller for each drone
        self.__cmd: List[str] = []                  # List of delivery commands

    def __verifyMission(self, drone: Drone, time: int, missionType: MissionType) -> None:
        if drone not in self.__mission:
            raise RuntimeError("Drone mission has not been instantiated properly")
        if self.__mission[drone].missionType != missionType:
            raise RuntimeError("Trying to sample drone wrong mission")
        if time < self.__mission[drone].time:
            raise RuntimeError("Cannot sample a drone before its mission started")
        if time != drone.time() and time - drone.time() != 1:
            raise RuntimeError("During a mission drone must be sampled at each time step")

    def isInMission(self, drone: Drone) -> bool:
        if drone in self.__mission:
            return True
        return False

    def mission(self, drone: Drone) -> MissionType:
        if not self.isInMission(drone):
            raise RuntimeError("Drone is not on a mission")
        return self.__mission[drone].missionType

    def setLoadMission(self, drone: Drone, warehouse: Warehouse, order: Inventory, time: int, book = True) -> None:
        """
        Set a loading mission for a drone
        :param drone:       Drone to set a mission
        :param warehouse:   Warehouse destination for loading
        :param order:       Order of products to load
        :param time:        Loading mission start time
        :param book         Whether to book order at warehouse in advance for future supply
        :return:
        """
        if drone in self.__mission:
            raise RuntimeError("Drone is already in a mission")
        self.__mission[drone] = Mission(MissionType.Load, time, order, warehouse = warehouse)
        if book:
            warehouse.book(order)   # Book order at the warehouse to guarantee it will be there where the drone arrives
        drone.refreshDroneStatus(time)      # Refresh drone status - sets drone clock to mission start time

    def load(self, drone: Drone, time: int) -> None:
        """
        Sample a drone during its loading mission
        :param drone:       Drone to sample
        :param time:        Sample time step
        :return:
        """
        self.__verifyMission(drone, time, MissionType.Load)

        ## At the beginning of the loading mission
        if time == drone.time():
            self.__mission[drone].travelPhase = True
            self.__mission[drone].loadUnloadPhase = True
            self.__command(drone)   # Parse command

        ## Traveling phase
        if self.__mission[drone].travelPhase:
            drone.travel(self.__mission[drone].warehouse.location(), time)
            self.__mission[drone].travelPhase = False
        if drone.status(time) != DroneStatus.Idle:  # Return if drone hasn't reached its destination
            return

        ## Loading phase
        if self.__mission[drone].loadUnloadPhase:
            for product in self.__mission[drone].order:
                nToLoad = self.__mission[drone].order[product]
                drone.load(product, nToLoad, time)
                self.__mission[drone].warehouse.remove(product, nToLoad, considerBooking=True)
            self.__mission[drone].loadUnloadPhase = False
        if drone.status(time) != DroneStatus.Idle:  # Return if drone hasn't completed loading
            return

        ## Mission complete
        del self.__mission[drone]

    def setDeliverMission(self, drone: Drone, customer: Customer, order: Inventory, time: int, book = True) -> None:
        """
        Set a deliver mission for a drone
        :param drone:       Drone to set a mission
        :param customer:    Customer to deliver products to
        :param order:       Order of products to load
        :param time:        Deliver mission start time
        :param book         Whether to book order at customer in advance for future supply
        :return:
        """
        if drone in self.__mission:
            raise RuntimeError("Drone is already in a mission")
        self.__mission[drone] = Mission(MissionType.Deliver, time, order, customer = customer)
        if book:
            customer.book(order)    # Book order delivery with customer, to avoid providing same products more than once
        drone.refreshDroneStatus(time)      # Refresh drone status - sets drone clock to mission start time

    def deliver(self, drone: Drone, time: int) -> None:
        """
        Sample a drone during its deliver mission
        :param drone:       Drone to sample
        :param time:        Sample time step
        :return:
        """
        self.__verifyMission(drone, time, MissionType.Deliver)

        ## At the beginning of the deliver mission
        if time == drone.time():
            self.__mission[drone].travelPhase = True
            self.__mission[drone].loadUnloadPhase = True
            self.__command(drone)   # Parse command

        ## Traveling phase
        if self.__mission[drone].travelPhase:
            drone.travel(self.__mission[drone].customer.location(), time)
            self.__mission[drone].travelPhase = False
        if drone.status(time) != DroneStatus.Idle:  # Return if drone hasn't reached its destination
            return

        ## Deliver phase
        if self.__mission[drone].loadUnloadPhase:
            for product in self.__mission[drone].order:
                nToDeliver = self.__mission[drone].order[product]
                drone.unload(product, nToDeliver, time)
                self.__mission[drone].customer.remove(product, nToDeliver, considerBooking=True)
            self.__mission[drone].loadUnloadPhase = False
        if drone.status(time) != DroneStatus.Idle:  # Return if drone hasn't completed delivering
            return

        ## Mission complete
        del self.__mission[drone]

    def setLoadAndDeliverMission(
            self, drone: Drone, warehouse: Warehouse, customer: Customer, order: Inventory, time: int, book = True) -> \
            None:
        """
        Set a combined mission that starts with a loading mission, followed by a deliver mission
        :param drone:       Drone to set a mission
        :param warehouse:   Warehouse destination for loading
        :param customer:    Customer to deliver products to
        :param order:       Order of products to load
        :param time:        Mission start time
        :param book         Whether to book order at customer and warehouse in advance for future supply
        :return:
        """
        if drone in self.__mission:
            raise RuntimeError("Drone is already in a mission")
        self.__mission[drone] = Mission(
            MissionType.LoadAndDeliver, time, order, warehouse = warehouse, customer = customer)
        drone.refreshDroneStatus(time)      # Refresh drone status - sets drone clock to mission start time
        if book:
            warehouse.book(order)  # Book order at the warehouse to guarantee it will be there where the drone arrives
            customer.book(order)    # Book order delivery with customer, to avoid providing same products more than once

    def __command(self, drone: Drone) -> None:
        order = self.__mission[drone].order
        if self.__mission[drone].missionType == MissionType.Load:
            warehouse = self.__mission[drone].warehouse
            for product in order:
                self.__cmd.append(f'{drone.index()} L {warehouse.index()} {product.index} {order[product]}')
        elif self.__mission[drone].missionType == MissionType.Deliver:
            customer = self.__mission[drone].customer
            for product in order:
                self.__cmd.append(f'{drone.index()} D {customer.index()} {product.index} {order[product]}')

    def getCommands(self) -> List[str]:
        return self.__cmd

    def sampleDrone(self, drone: Drone, time: int) -> None:
        """
        Sample a drone at a given time
        :param drone:       Drone to sample
        :param time:        Current time
        :return:
        """
        if drone not in self.__mission:
            raise RuntimeError("Drone mission has not been instantiated properly")

        # ## At the beginning of a mission, parse a command

        ## Time step for drone mission
        if self.__mission[drone].missionType == MissionType.Load:
            self.load(drone, time)
        elif self.__mission[drone].missionType == MissionType.Deliver:
            self.deliver(drone, time)
        elif self.__mission[drone].missionType == MissionType.LoadAndDeliver:
            if self.__mission[drone].loadPhase:
                mission = self.__mission[drone]
                self.__mission[drone].missionType = MissionType.Load
                self.load(drone, time)
                if drone in self.__mission:     # Loading mission has not finished
                    self.__mission[drone].missionType = MissionType.LoadAndDeliver
                    return
                self.__mission[drone] = mission
                self.__mission[drone].loadPhase = False
            self.__mission[drone].missionType = MissionType.Deliver
            self.deliver(drone, time)
            if drone in self.__mission:     # Deliver mission has not finished
                self.__mission[drone].missionType = MissionType.LoadAndDeliver

class TestDelivery(unittest.TestCase):
    def setUp(self):
        self.drone = Drone ((0, 0), 21, inventory=Inventory())
        warehouseInventory = Inventory()
        self.product0 = Product(0, 5)
        self.product1 = Product(2, 3)
        warehouseInventory.append(self.product0, 10)
        warehouseInventory.append(self.product1, 4)
        self.warehouse = Warehouse ((1, 1), warehouseInventory)
        customerOrder = Inventory()
        customerOrder.append(self.product0, 3)
        self.customer = Customer((2, 3), customerOrder)

    def test_load(self):
        nWarehouseBeforeLoad = self.warehouse.order().count(self.product1)
        nDroneBeforeLoad = self.drone.inventory(0).count(self.product1)
        productsToLoad = Inventory()
        productsToLoad.append(self.product0, 3)
        productsToLoad.append(self.product1, 2)
        delivery = Delivery()
        delivery.setLoadMission(self.drone, self.warehouse, productsToLoad, 0)
        for time in range(4):
            delivery.sampleDrone(self.drone, time)
        nWarehouseAfterLoad = self.warehouse.order().count(self.product1)
        nDroneAfterLoad = self.drone.inventory(14).count(self.product1)
        droneLocationAfterLoad = self.drone.location(14)
        self.assertEqual(nWarehouseAfterLoad, nWarehouseBeforeLoad - 2)
        self.assertEqual(nDroneBeforeLoad, nDroneAfterLoad - 2)
        self.assertEqual(droneLocationAfterLoad, self.warehouse.location())

    def test_deliver(self):
        productsToDeliver = Inventory()
        productsToDeliver.append(self.product0, 2)
        self.drone = Drone((0, 0), 21, productsToDeliver)
        delivery = Delivery()
        delivery.setDeliverMission(self.drone, self.customer, productsToDeliver, 0)
        time = 0
        while delivery.isInMission(self.drone):
            delivery.sampleDrone(self.drone, time)
            time += 1
        self.assertEqual(self.drone.inventory(time).count(self.product0), 0)
        self.assertEqual(self.drone.location(time), self.customer.location())

    def test_load_and_deliver(self):
        delivery = Delivery()
        productsToDeliver = Inventory()
        productsToDeliver.append(self.product0, 2)
        time = 0
        delivery.setLoadAndDeliverMission(self.drone, self.warehouse, self.customer, productsToDeliver, time)
        while delivery.isInMission(self.drone):
            delivery.sampleDrone(self.drone, time)
            time += 1

    @staticmethod
    def __distance (orig,dest):
        return np.ceil(np.sqrt(np.power(orig[0] - dest[0], 2) + np.power(orig[1] - dest[1], 2)))

if __name__ == '__main__':
    unittest.main()
