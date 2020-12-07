import sys
from Parser import Parser
from Delivery import Delivery
from Drone import Drone, DroneStatus
from typing import List, Dict, Set
from OrderInventory import Order, Inventory
from WarehouseCustomer import Warehouse, Customer
from Definitions import distance, Products
import numpy as np
from itertools import cycle

class Simulations:
    def __init__(self, inputFilename):
        self.params = Parser(inputFilename)
        self.drones: List[Drone] = []
        for i in range(self.params.nDrones):
            self.drones.append(
                Drone(self.params.warehouses[0].location, self.params.maxPayload, Inventory(), index = i))
        self._points = 0
        self._completedOrders: Set[Customer] = set()
        self._d = Delivery()

    def _printInventories(self, time: int) -> None:
        print("Time: ", time)
        print("Drones")
        for drone in self.drones:
            if drone.task.status == DroneStatus.Traveling:
                msg = "Traveling to -> " + str(drone.task.dest)
            elif drone.task.status == DroneStatus.Load:
                msg = "Loading at -> " + str(drone.location(time))
            elif drone.task.status == DroneStatus.Unload:
                msg = "Unloading at -> " + str(drone.location(time))
            else:
                msg = "Idle"
            print(drone.index(), ": ", drone.inventory(time), ". ", msg)
        print("Warehouses")
        for warehouse in self.params.warehouses:
            print(warehouse.index(), warehouse.location, ": ", warehouse.inventory)
        print("Customers")
        for customer in self.params.customers:
            print(customer.index(), customer.location, ": ", customer.order)
        print("Points: ", str(self._points))
        print("===================================")

    def _printProgress(self, time: int) -> None:

        # Completed orders
        nCompleted = 0
        for customer in self.params.customers:
            if customer.isComplete():
                nCompleted += 1

        # Drone operations
        nDronesIdle = 0
        nDronesTraveling = 0
        nDronesLoading = 0
        nDronesUnloading = 0
        for drone in self.drones:
            if drone.task.status == DroneStatus.Traveling:
                nDronesTraveling += 1
            elif drone.task.status == DroneStatus.Load:
                nDronesLoading += 1
            elif drone.task.status == DroneStatus.Unload:
                nDronesUnloading += 1
            else:
                nDronesIdle += 1

        print("Time: " + str(time) + "/" + str(self.params.nTurns) + 
              ": Completed orders: " + str(nCompleted) + "/" + str(len(self.params.customers)),
              " Drones (Idle, Traveling, Loading, Unloading): " +
              str(nDronesIdle), str(nDronesTraveling), str(nDronesLoading), str(nDronesUnloading),
              " Points: ", str(self._points))

    def _score(self, time) -> int:
            return np.ceil((self.params.nTurns - time) / self.params.nTurns * 100)

    def _allOrdersCompleted(self) -> bool:
        for customer in self.params.customers:
            if not customer.isComplete():
                return False
        return True

    def writeCommands(self, outputFilename: str) -> None:
        f = open(outputFilename, 'w')
        cmds = self._d.getCommands()
        f.write(f'{len(cmds)}\n')
        for cmd in cmds:
            f.write(f'{cmd}\n')
        f.close()

class Model0(Simulations):
    def __init__(self, inputFilename):
        super().__init__(inputFilename)
        self.__service: Dict[Drone, List[Customer]] = {}   # A list of customers each drone services

    def __assignDronesToCustomers(self):
        drones_cycle = cycle(self.drones)
        itDrone = iter(drones_cycle)
        for customer in self.params.customers:
            drone = next(itDrone)
            if drone not in self.__service:
                self.__service[drone]: List[Customer] = []
            self.__service[drone].append(customer)

    def __getNotCompleteCustomer(self, drone: Drone) -> Customer:
        customers = self.__service[drone]
        for customer in customers:
            if not customer.isComplete():
                return customer
        return Customer()

    def run(self) -> None:
        self.__assignDronesToCustomers()
        self._points = 0

        ### Main loop over time steps
        for time in range(self.params.nTurns):

            ## Send idle drones to warehouse
            for drone in self.drones:
                if self._d.isInMission(drone):            # Skip busy drones
                    continue
                if drone not in self.__service:     # Skip drones that do not fly
                    continue
                if len(self.__service[drone]) == 0: # No more customers to serve by this drone
                    continue

                # For the current drone, find closest warehouse that can serve customer, at least partially
                customer = self.__getNotCompleteCustomer(drone)
                if customer.isComplete():       # All order related with current drone have been completed
                    continue
                warehouse = self.__closestServingWarehouse(customer)
                availableOrder = warehouse.createAvailableOrder(customer.order)
                if availableOrder.empty():
                    continue

                # Adjusting order to current drone weight limits
                availableOrder = self.__loadMaximalPossible(drone, availableOrder)

                # Send the drone to a load-and-deliver mission between the chosen warehouse and the customer
                self._d.setLoadAndDeliverMission(drone, warehouse, customer, availableOrder, time)

            ## Sample all drone for current time
            for drone in self.drones:
                if self._d.isInMission(drone):
                    self._d.sampleDrone(drone, time)

            ## Update scoring
            for customer in self.params.customers:
                if customer.isComplete() and customer not in self._completedOrders:
                    self._points += self._score(time)
                    self._completedOrders.add(customer)     # Regsiter completed order, to not count them again

            # self._printInventories(time)
            self._printProgress(time)

            # Return if all orders completed
            if self._allOrdersCompleted():
                return

    def __closestServingWarehouse(self, customer: Customer) -> Warehouse:
        order = customer.order
        warehouses = self.params.warehouses
        minDist = distance((0, 0), (self.params.nRows, self.params.nColumns))
        closestWarehouse = warehouses[0]
        for warehouse in warehouses:
            availableOrder = warehouse.createAvailableOrder(order)
            if availableOrder.empty():
                continue
            d = distance(warehouse.location, customer.location)
            if d < minDist:
                minDist = d
                closestWarehouse = warehouse
        return closestWarehouse

    def __loadMaximalPossible(self, drone: Drone, order: Order) -> Order:
        products: Products = []
        for product in order:
            for i in range(order[product]):
                products.append(product)
        products.sort(key=lambda product: product.weight, reverse=True)
        w = 0
        maxWeight = drone.maxWeight
        maxOrder = Order()
        for i, product in enumerate(products):
            if w + product.weight > maxWeight:
                break
            maxOrder.append(product, 1)
            w += product.weight
        del products[:i + 1]        # Delete heaviest products that cannot be added to the drone
        for product in reversed(products):  # Try and add lighter products, if there is room in teh drone
            if w + product.weight > maxWeight:
                break
            maxOrder.append(product, 1)
            w += product.weight
        return maxOrder

if __name__ == '__main__':
    if len(sys.argv) == 1:
        # inputFilename = 'SmallInput.dat'
        inputFilename = 'busy_day.in'
    else:
        inputFilename = sys.argv[1]
    sim = Model0(inputFilename)
    sim.run()
    sim.writeCommands('output.dat')


