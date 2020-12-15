import unittest
from Parser import Parser
from Delivery import Delivery, MissionType
from Drone import Drone, DroneStatus
from typing import List, Dict, Set, Tuple
from OrderInventory import Order, Inventory
from WarehouseCustomer import Warehouse, Customer
from Definitions import distance, Products
import numpy as np
from itertools import cycle
from enum import Enum, auto
import copy

class SimulationPrintouts(Enum):
    Nothing = auto()
    Inventories = auto()
    Progress = auto()

class Simulations:
    def __init__(self, inputFilename):
        self.params = Parser(inputFilename)
        self.drones: List[Drone] = []
        for i in range(self.params.nDrones):
            self.drones.append(
                Drone(self.params.warehouses[0].location(), self.params.maxPayload, Inventory(), index = i))
        self._points = 0
        self._completedOrders: Set[Customer] = set()
        self._d = Delivery()

    def run(self, printouts = SimulationPrintouts.Nothing) -> None:
        self._points = 0
        self._timeStepZero()        # Model specific initialization (zero time step)

        ### Main loop over time steps
        for time in range(self.params.nTurns):

            ## Model specific time step
            self._timeStep(time)

            ## Sample all drone for current time
            for drone in self.drones:
                if self._d.isInMission(drone):
                    self._d.sampleDrone(drone, time)

            ## Update scoring
            for customer in self.params.customers:
                if customer.isComplete():
                    self._points += self._score(time)
                    self._completedOrders.add(customer)     # Register completed order, to not count them again

            # Removing completed customers
            self.params.customers[:] = [x for x in self.params.customers if not x.isComplete()]

            ## Printouts
            if printouts == SimulationPrintouts.Inventories:
                self._printInventories(time)
            elif printouts == SimulationPrintouts.Progress:
                self._printProgress(time)

            # Return if all orders completed
            if self._allOrdersCompleted():
                return

    def _orderWeightOriginal(self) -> Dict[Customer, float]:
        orderWeights: Dict[Customer, int] = {}
        for customer in self.params.customers:
            orderWeights[customer] = customer.order().weight()
        return orderWeights

    def _timeStepZero(self) -> None:
        raise NotImplementedError("Zero time step should be model specific")

    def _timeStep(self, time: int) -> None:
        raise NotImplementedError("Time step should be model specific")

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
            print(warehouse.index(), warehouse.location(), ": ", warehouse.order())
        print("Customers")
        for customer in self.params.customers:
            print(customer.index(), customer.location(), ": ", customer.order())
        print("Points: ", str(self._points))
        print("===================================")

    def _printProgress(self, time: int) -> None:

        # Drone operations
        nDronesIdle = 0
        nDronesTraveling = 0
        nDronesLoading = 0
        nDronesUnloading = 0
        averageDroneWeight = 0
        for drone in self.drones:
            averageDroneWeight += drone.inventory(time).weight()
            if drone.task.status == DroneStatus.Traveling:
                nDronesTraveling += 1
            elif drone.task.status == DroneStatus.Load:
                nDronesLoading += 1
            elif drone.task.status == DroneStatus.Unload:
                nDronesUnloading += 1
            else:
                nDronesIdle += 1
        averageDroneWeight /= len(self.drones)

        print("Time: " + str(time) + "/" + str(self.params.nTurns) + 
              ": Completed orders: " + str(len(self._completedOrders)) + "/" + str(self.params.nOrders),
              " Drones (Idle, Traveling, Loading, Unloading): " +
              str(nDronesIdle), str(nDronesTraveling), str(nDronesLoading), str(nDronesUnloading),
              " Ave. drone weight: ", str(averageDroneWeight),
              " Points: ", str(self._points))

    def _score(self, time) -> int:
            return np.ceil((self.params.nTurns - time) / self.params.nTurns * 100)

    def _allOrdersCompleted(self) -> bool:
        for customer in self.params.customers:
            if not customer.isComplete():
                return False
        return True

    def _closestServingWarehouse(self, customer: Customer) -> Tuple[Warehouse, Inventory]:
        """
        Given a customer, find the its closest warehouse that can serve it
        :param customer:    A customer
        :return:
        """

        ## Find minimal distance between customer and warehouse that can serve
        order = customer.getProductsMinusBookings()
        warehouses = self.params.warehouses
        minDist = distance((0, 0), (self.params.nRows, self.params.nColumns))
        closestWarehouse = warehouses[0]
        closestAvailableOrder = Inventory()
        for warehouse in warehouses:
            availableOrder = warehouse.createAvailableOrder(order)  # What can the warehouse offer to the customer?
            if availableOrder.empty():  # If nothing, ignore this warehouse
                continue
            d = distance(warehouse.location(), customer.location())
            if d < minDist:
                minDist = d
                closestWarehouse = warehouse
                closestAvailableOrder = availableOrder
        return closestWarehouse, closestAvailableOrder

    def writeCommands(self, outputFilename: str) -> None:
        f = open(outputFilename, 'w')
        cmds = self._d.getCommands()
        f.write(f'{len(cmds)}\n')
        for cmd in cmds:
            f.write(f'{cmd}\n')
        f.close()

    def _maximalPossibleLoad(self, drone: Drone, order: Order, time: int) -> Inventory:
        """
        Find an order which is a subset of a given order, which fits a drone maximal capacity constraint
        :param drone:   Input drone
        :param order:   Order of which a weight limited order should be created
        :return:
        """
        if order.empty():
            return Inventory()
        products: Products = []     # A list of product in the order - expansion of order to single repeating items
        for product in order:
            for i in range(order[product]):
                products.append(product)
        products.sort(key=lambda product: product.weight, reverse=True)     # Sort product form the heaviest first
        w = drone.inventory(time).weight()
        maxWeight = drone.maxWeight
        maxOrder = Inventory()
        i = 0
        for product in products:        # Try to load the heaviest first
            if w + product.weight > maxWeight:
                break
            maxOrder.append(product, 1)
            w += product.weight
            i += 1
        del products[:i + 1]        # Delete heaviest products that cannot be added to the drone
        for product in reversed(products):  # Try and add lighter products, if there is room in the drone
            if w + product.weight > maxWeight:
                break
            maxOrder.append(product, 1)
            w += product.weight
        return maxOrder

    def _customerWarehouseDistances(self) -> Dict[Tuple[Warehouse, Customer], int]:
        """
        Calculates all distances between warehouses and customers
        :return:
        """
        dist: Dict[Tuple[Warehouse, Customer], int] = {}
        for warehouse in self.params.warehouses:
            for customer in self.params.customers:
                dist[(warehouse, customer)] = distance(warehouse.location(), customer.location())
        return dist

    def _customerWarehouseDistances2(self) -> Dict[Tuple[Warehouse, Customer], int]:
        """
        Calculates all distances between warehouses and customers
        :return:
        """
        dist: Dict[Tuple[Warehouse, Customer], int] = {}
        for warehouse in self.params.warehouses:
            for customer in self.params.customers:
                d = distance(warehouse.location(), customer.location())
                dist[(warehouse, customer)] = d * d
        return dist

    def _weightedCustomerWarehouseDistances(self) -> Dict[Tuple[Warehouse, Customer], int]:
        """
        Calculates all distances between warehouses and customers, weighted by the total weight of customer initial
        orders. Affects heaviers customer to be served first
        :return:

        """
        dist: Dict[Tuple[Warehouse, Customer], int] = {}
        for warehouse in self.params.warehouses:
            for customer in self.params.customers:
                dist[(warehouse, customer)] = distance(warehouse.location(), customer.location()) * \
                                              customer.order().weight()
        return dist

class Model0(Simulations):
    def __init__(self, inputFilename):
        super().__init__(inputFilename)
        self.__service: Dict[Drone, List[Customer]] = {}   # A list of customers each drone services

    def _timeStepZero(self) -> None:
        self.__assignDronesToCustomers()

    def _timeStep(self, time: int) -> None:

        ## Send idle drones to warehouse
        for drone in self.drones:
            if self._d.isInMission(drone):  # Skip busy drones
                continue
            if drone not in self.__service:  # Skip drones that do not fly
                continue
            if len(self.__service[drone]) == 0:  # No more customers to serve by this drone
                continue

            # For the current drone, find closest warehouse that can serve customer, at least partially
            customer = self.__getNotCompleteCustomer(drone)
            if customer.isComplete():  # All order related with current drone have been completed
                continue
            warehouse, availableOrder = self._closestServingWarehouse(customer)
            if availableOrder.empty():
                continue

            # Adjusting order to current drone weight limits
            availableOrder = self._maximalPossibleLoad(drone, availableOrder, time)

            # Send the drone to a load-and-deliver mission between the chosen warehouse and the customer
            self._d.setLoadAndDeliverMission(drone, warehouse, customer, availableOrder, time)

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

class Model1(Simulations):
    def __init__(self, inputFilename):
        super().__init__(inputFilename)

    def _timeStepZero(self) -> None:
        pass

    def _timeStep(self, time: int) -> None:

        ## Set mission to idle drones
        for drone in self.drones:
            if self._d.isInMission(drone):  # Skip busy drones
                continue

            # Decide which customer to serve, based on the order weight to complete (the smaller the better)
            lighestCustomer = self.__lightestCustomer()
            if lighestCustomer.isComplete():
                continue

            # Find the warehouse that has most of what the customer needs
            warehouse, availableOrder = self.__mostSuitableWarehouse(drone, lighestCustomer)

            # Load and deliver between chosen warehouse and customer
            self._d.setLoadAndDeliverMission(drone, warehouse, lighestCustomer, availableOrder, time)

    def __lightestCustomer(self) -> Customer:
        w = max(self.params.customers, key=lambda c: c.order().weight()).order().weight()
        lighestCustomer = Customer()
        for customer in self.params.customers:
            if customer.isComplete():
                continue
            customerRemainingOrder = customer.getProductsMinusBookings()
            if customerRemainingOrder.weight() < w:
                w = customerRemainingOrder.weight()
                lighestCustomer = customer
        return lighestCustomer

    def __mostSuitableWarehouse(self, drone: Drone, customer: Customer) -> Tuple[Warehouse, Inventory]:
        maxWeight: int = 0
        minDist = distance((0, 0), (self.params.nRows, self.params.nColumns))
        bestWarehouse = Warehouse()
        bestAvailableOrder = Inventory()
        for warehouse in self.params.warehouses:
            customerRemainingOrder = customer.getProductsMinusBookings()
            availableOrder = warehouse.createAvailableOrder(customerRemainingOrder)
            if availableOrder.empty():
                continue
            availableOrder = self._maximalPossibleLoad(drone, availableOrder)
            d = distance(warehouse.location(), customer.location())
            if d < minDist:
                maxWeight = 0
                minDist = d
                bestWarehouse = warehouse
                bestAvailableOrder = availableOrder
            elif d == minDist and availableOrder.weight() > maxWeight:
                maxWeight = availableOrder.weight()
                bestWarehouse = warehouse
                bestAvailableOrder = availableOrder
        return bestWarehouse, bestAvailableOrder

class Model2(Simulations):
    def __init__(self, inputFilename):
        super().__init__(inputFilename)

    def _timeStepZero(self) -> None:
        pass

    def _timeStep(self, time: int) -> None:

        ## Set mission to idle drones
        for drone in self.drones:
            if self._d.isInMission(drone):  # Skip busy drones
                continue

            # Find customer closest to drone, and best warehouse to serve it
            warehouse, customer, products = self.__findOptimalCustomerWarehouse(drone, time)
            if products.empty():
                continue

            # Deliver between the two
            self._d.setLoadAndDeliverMission(drone, warehouse, customer, products, time)

    def __findOptimalCustomerWarehouse(self, drone: Drone, time: int) -> Tuple[Warehouse, Customer, Inventory]:
        minDist = distance((0, 0), (self.params.nRows, self.params.nColumns))   # Minimal distance of customer to drone
        closestWarehouse = Warehouse()
        closestCustomer = Customer()
        closestAvailableOrder = Inventory()
        for customer in self.params.customers:
            if customer.isComplete():
                continue
            d = distance(drone.location(time), customer.location())
            if d < minDist:
                minDist = d
                warehouse, availableOrder = self._closestServingWarehouse(customer)
                if availableOrder.empty():
                    continue

                # Adjusting order to current drone weight limits
                closestAvailableOrder = self._maximalPossibleLoad(drone, availableOrder, time)

                closestCustomer = customer
                closestWarehouse = warehouse
        return closestWarehouse, closestCustomer, closestAvailableOrder

class Model3(Simulations):
    def __init__(self, inputFilename):
        super().__init__(inputFilename)

    def _timeStepZero(self) -> None:
        pass

    def _timeStep(self, time: int) -> None:

        ## Set mission to idle drones
        for drone in self.drones:
            if self._d.isInMission(drone):  # Skip busy drones
                continue

            # Find warehouse-customer pair that will establish the shortest route for the current drone
            warehouse, customer, products = self.__findOptimalCustomerWarehouse(drone, time)
            if products.empty():
                continue

            # Deliver between the two
            self._d.setLoadAndDeliverMission(drone, warehouse, customer, products, time)

    def __findOptimalCustomerWarehouse(self, drone: Drone, time: int) -> Tuple[Warehouse, Customer, Inventory]:
        optimalWarehouse = Warehouse()
        optimalCustomer = Customer()
        optimalProducts = Inventory()
        minPath = 2 * distance((0, 0), (self.params.nRows, self.params.nColumns))
        for customer in self.params.customers:
            if customer.isComplete(True):
                continue
            order = customer.getProductsMinusBookings()
            for warehouse in self.params.warehouses:
                dWarehouseCustomer = distance(warehouse.location(), customer.location())
                dDroneWarehouse = distance(warehouse.location(), drone.location(time))
                if dWarehouseCustomer + dDroneWarehouse < minPath:
                    availableOrder = warehouse.createAvailableOrder(order)  # What can the warehouse offer to the
                                                                            # customer?
                    availableOrder = self._maximalPossibleLoad(drone, availableOrder, time)
                    if not availableOrder.empty():
                        minPath = dWarehouseCustomer + dDroneWarehouse
                        optimalWarehouse = warehouse
                        optimalCustomer = customer
                        optimalProducts = availableOrder

        return optimalWarehouse, optimalCustomer, optimalProducts

class DroneMission:
    def __init__(self, missionType: MissionType, products: Inventory, customer: Customer = None):
        if customer is None:
            customer = Customer()
        self.missionType = missionType
        self.products = products
        self.customer = customer

class CustomerPicking(Enum):        # How to give precedence to customers
    ClosestCurrent = "ClosestCurrent"             # Customers that are closest to warehouse at a given time
    WeightedClosestCurrent = "WeightedClosestCurrent"     # Distance weighted by customer order weight at a given time
    WeightedClosestInitial = "WeightedClosestInitial"     # Distance weighted by customer order weight at time 0
    Weighted2ClosestCurrent = "Weighted2ClosestCurrent"
    WeightedClosest2tCurrent = "WeightedClosest2tCurrent"
    RatioClosestCurrent = "RatioClosestCurrent"

class Model4(Simulations):
    def __init__(self, inputFilename, customerPicking: CustomerPicking):
        super().__init__(inputFilename)
        self.__service: Dict[Drone, Warehouse] = {}     # Warehouse each drone serves (assuming 1 warehousee is served
                                                        # by number of drones)
        self.__missionPlan: Dict[Drone, List[DroneMission]] = {}
        self.__dist: Dict[Tuple[Warehouse, Customer], int] = {}
        self.__warehousesToExclude: Dict[Drone, List[Warehouse]] = {}
        self.__customerPicking = customerPicking
        print(self.__customerPicking)
        self.orderWeights = self._orderWeightOriginal()

    def _timeStepZero(self) -> None:
        # self.__assignWarehousesToDrones()                   # Assign for each warehouse, the drones that will serve it
        if self.__customerPicking == CustomerPicking.ClosestCurrent or \
                self.__customerPicking == CustomerPicking.WeightedClosestCurrent or \
                self.__customerPicking == CustomerPicking.Weighted2ClosestCurrent or \
                self.__customerPicking == CustomerPicking.RatioClosestCurrent:
            self.__dist = self._customerWarehouseDistances()  # Calculate distances between all warehouses and customers
        elif self.__customerPicking == CustomerPicking.WeightedClosest2tCurrent:
            self.__dist = self._customerWarehouseDistances2()
        elif self.__customerPicking == CustomerPicking.WeightedClosestInitial:
            self.__dist = self._weightedCustomerWarehouseDistances()

    def __assignWarehousesToDrones(self) -> None:
        self.__service.clear()
        warehouse_cycle = cycle(self.params.warehouses)
        itWarehouse = iter(warehouse_cycle)
        for drone in self.drones:
            warehouse = next(itWarehouse)
            if drone in self.__service:
                raise RuntimeError("Cannot assign a drone to more than one warehouse")
            self.__service[drone] = warehouse

    def _timeStep(self, time: int) -> None:

        ## Send idle drones to warehouse
        for drone in self.drones:
            # warehouse = self.__service[drone]

            ## Planing drone mission
            if not self._d.isInMission(drone) and drone not in self.__missionPlan:

                # Pick warehouse closest to the drone - exclude closer ones that were picked before, but couldn't serve
                bestWarehouse = Warehouse()
                bestWarehouseOrder = Inventory()
                bestCustomers: List[Customer] = []
                bestCustomerOrder: List[Inventory] = []
                maxWeightCustomerOrders = 0
                while True:
                    if drone not in self.__warehousesToExclude:
                        self.__warehousesToExclude[drone] = []
                    warehouse = self.__closestWarehouseToDrone(drone, time)
                    if warehouse.order().empty():
                        self.__warehousesToExclude[drone].append(warehouse)
                        continue

                    # For the current served warehouse, compose the list of customers to deliver to
                    customers, customerOrders, warehouseOrder = \
                        self._composeDeliverredCustomers(drone, warehouse, time)

                    if warehouseOrder.weight() > maxWeightCustomerOrders:
                        maxWeightCustomerOrders = warehouseOrder.weight()
                        bestWarehouse = warehouse
                        bestCustomers = customers
                        bestCustomerOrder = customerOrders
                        bestWarehouseOrder = warehouseOrder
                    self.__warehousesToExclude[drone].append(warehouse)
                    if len(self.__warehousesToExclude[drone]) == len(self.params.warehouses):
                        break
                self.__warehousesToExclude[drone].clear()

                # First mission is to load from a warehouse
                bestWarehouse.book(bestWarehouseOrder)
                self.__service[drone] = bestWarehouse
                self.__missionPlan[drone] = []
                self.__missionPlan[drone].append(DroneMission(MissionType.Load, bestWarehouseOrder))

                # Append delivery missions to chosen customers
                for (customer, customerOrder) in zip(bestCustomers, bestCustomerOrder):
                    customer.book(customerOrder)
                    self.__missionPlan[drone].append(
                        DroneMission(MissionType.Deliver, customerOrder, customer = customer))

            # Set next drone sub-mission, and pop it from the drone mission list
            if not self._d.isInMission(drone) and len(self.__missionPlan[drone]) > 0:
                self._setNextDroneMission(drone, time)

    def __closestWarehouseToDrone(self, drone: Drone, time: int) -> Warehouse:
        minDist = distance((0, 0), (self.params.nRows, self.params.nColumns))
        closetWarehouse = Warehouse()
        for warehouse in self.params.warehouses:
            if warehouse in self.__warehousesToExclude[drone]:
                continue
            d = distance(drone.location(time), warehouse.location())
            if d < minDist:
                minDist = d
                closetWarehouse = warehouse
        return closetWarehouse

    def _composeDeliverredCustomers(self, drone: Drone, warehouse: Warehouse, time: int) ->\
        Tuple[List[Customer], List[Inventory], Inventory]:
        """
        Creates lists of orders to load from a warehouse and deliver to a list of customers - mission planing
        :param warehouse:
        :return:
        """

        ## Sort customers to increasing distance from warehouse (closest first)
        if self.__customerPicking == CustomerPicking.WeightedClosestCurrent or\
                self.__customerPicking == CustomerPicking.WeightedClosest2tCurrent:    # Based on current weight
            self.params.customers.sort(key=lambda x: self.__dist[(warehouse, x)] * x.order().weight())
        elif self.__customerPicking == CustomerPicking.Weighted2ClosestCurrent:
            self.params.customers.sort(key=lambda x: self.__dist[(warehouse, x)] *
                                                     x.order().weight() * x.order().weight())
        elif self.__customerPicking == CustomerPicking.RatioClosestCurrent:
            self.params.customers.sort(key=lambda x: self.__dist[(warehouse, x)] *
                                                     self.orderWeights[x] / x.order().weight())
        else:       # Based on weights and distances at time 0
            self.params.customers.sort(key=lambda x: self.__dist[(warehouse, x)])

        ## Iterating of customers, starting from the closest - adding customers that can be served by the warehouse
        customersToDeliver: List[Customer] = []          # List of customers that will be delivered
        customerOrders: List[Inventory] = []    # List of products each customer will receive
        droneTmp = copy.deepcopy(drone)         # A temp drone copy to simulate future drone loadings
        warehouseOrder = Inventory()            # The total warehouse order
        warehouseTmp = copy.deepcopy(warehouse)
        for i in range(len(self.params.customers)):
            customer = self.params.customers[i] # copy.deepcopy(self.params.customers[i])
            if customer.isComplete():
                continue
            customerOrder = customer.getProductsMinusBookings()     # Get its updated order (minus booking)
            availableOrder = warehouseTmp.createAvailableOrder(customerOrder)       # Consider warehouse availability
            availableOrder = self._maximalPossibleLoad(droneTmp, availableOrder, time)    # Consider drone capacity
            if availableOrder.empty():      # Skip to te next customer, if no available order is found
                continue
            customersToDeliver.append(customer) # append(self.params.customers[i])
            customerOrders.append(availableOrder)
            for product in availableOrder:  # Add products to warehouse order
                warehouseOrder.append(product, availableOrder[product])
                droneTmp.inventory(time).append(product, availableOrder[product])   # Load dummy drone to consider its
                                                                                    # capacity for the next customer
            warehouseTmp.book(availableOrder)   # Prevent future over-booking by other customers in current loop

        return customersToDeliver, customerOrders, warehouseOrder

    def _setNextDroneMission(self, drone: Drone, time: int) -> None:
        missionType = self.__missionPlan[drone][0].missionType
        products = self.__missionPlan[drone][0].products

        # Set relevant mission. Don't book, because booking was already set during mission planning
        if missionType == MissionType.Load:
            warehouse = self.__service[drone]
            self._d.setLoadMission(drone, warehouse, products, time, book = False)
        elif missionType == MissionType.Deliver:
            customer = self.__missionPlan[drone][0].customer
            self._d.setDeliverMission(drone, customer, products, time, book = False)
        self.__missionPlan[drone].pop(0)   # Pop the mission that was set
        if len(self.__missionPlan[drone]) == 0:
            del self.__missionPlan[drone]

class Model5(Simulations):
    def __init__(self, inputFilename):
        super().__init__(inputFilename)
        self.customersTmp: List[Customer] = []
        self.customerOrdersTmp: List[Inventory] = []
        self.optimalCustomers: List[Customer] = []
        self.optimalOrders: List[Inventory] = []
        self.orderWeights = self._orderWeightOriginal()

    def optimizeCustomers(self,
                          drone: Drone,
                          time: int,
                          warehouse: Warehouse,
                          optimalCustomers: List[Customer],
                          optimalOrders: List[Inventory]):
        self.__maxSumOfRatios = 0
        self.customersTmp.clear()
        self.customerOrdersTmp.clear()
        self.optimalCustomers.clear()
        self.optimalOrders.clear()
        drone.task.status = DroneStatus.Load
        for customer in self.params.customers:
            self.__optimizeCustomersUtil(drone, time, customer, warehouse, 0)

    def __optimizeCustomersUtil(self,
                                drone: Drone,
                                time: int,
                                customer: Customer,
                                warehouse: Warehouse,
                                sumOfRatios: float) -> None:
        customerOrder = customer.getProductsMinusBookings()
        availableOrder = warehouse.createAvailableOrder(customerOrder)
        availableOrder = self._maximalPossibleLoad(drone, availableOrder, time)
        if availableOrder.empty():
            return
        for product in availableOrder:
            drone.inventory(time).append(product, availableOrder[product])
        self.customersTmp.append(customer)
        self.customerOrdersTmp.append(availableOrder)
        sumOfRatios += availableOrder.weight() / self.orderWeights[customer]
        if sumOfRatios > self.__maxSumOfRatios:
            self.__maxSumOfRatios = sumOfRatios
            self.optimalCustomers = self.customersTmp
            self.optimalOrders = self.customerOrdersTmp
        for nextCustomer in self.params.customers:
            if nextCustomer in self.customersTmp:
                continue
            if distance(customer.location(), nextCustomer.location()) > 20:     # FIXME: Arbitrary
                continue
            self.__optimizeCustomersUtil(drone, time, nextCustomer, warehouse, sumOfRatios)
        for product in availableOrder:
            drone.inventory(time).remove(product, availableOrder[product])
        self.customersTmp.pop()
        self.customerOrdersTmp.pop()

class TestModel5(unittest.TestCase):
    def setUp(self):
        self.sim = Model5('busy_day.in')
        self.drone = self.sim.drones[0]
        self.warehouse = self.sim.params.warehouses[1]
        pass

    def test_optimize_customers(self):
        optimalCustomers: List[Customer] = []
        optimalOrders: List[Inventory] = []
        self.sim.optimizeCustomers(self.drone, 0, self.warehouse, optimalCustomers, optimalOrders)

if __name__ == '__main__':
    unittest.main()




