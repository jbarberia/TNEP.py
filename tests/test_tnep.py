"""import os
import pytest
from tnep import Parser
from tnep import TNEP
from tnep import Parameters

data_path = os.path.dirname(os.path.realpath(__file__)) + '\\data'
data = [data_path + '\\' + case for case in os.listdir(data_path)]

@pytest.mark.parametrize('filename', data)
def est_tnep(filename, parameter):
    net = Parser().parse(filename)
    parameters = Parameters.read('algo')
    model = TNEP()
    nets = model.solve()

    assert que todas las nets tengan las misma cantidad de lineas"""