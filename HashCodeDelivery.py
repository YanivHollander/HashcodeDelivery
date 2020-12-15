from Simulations import *
import sys

if __name__ == '__main__':
    # inputFilename = 'SmallInput.dat'
    inputFilename = 'busy_day.in'
    model = 'Model4'
    param = 'ClosestCurrent'
    if len(sys.argv) > 1:
        model = sys.argv[1]
    if len(sys.argv) > 2:
        param = sys.argv[2]
    outputFilename = "output" + model
    sim = Model0(inputFilename)
    if model == 'Model1':
        sim = Model1(inputFilename)
    elif model == 'Model2':
        sim = Model2(inputFilename)
    elif model == 'Model3':
        sim = Model3(inputFilename)
    elif model == 'Model4':
        outputFilename += param
        sim = Model4(inputFilename, CustomerPicking(param))
    sim.run(printouts = SimulationPrintouts.Progress)
    sim.writeCommands(outputFilename + ".dat")


