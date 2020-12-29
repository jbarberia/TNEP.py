import os
import pytest
from data import cases
from tnep import Parser
from tnep import NR


@pytest.mark.parametrize('filename', cases)
def test_ac_solve(filename):
    net = Parser().parse(filename)
    mis1 = net.bus_P_mis
    NR().solve_ac(net)
    mis2 = net.bus_P_mis
    
    assert abs(mis1) >= abs(mis2)

@pytest.mark.parametrize('filename', cases)
def test_dc_solve(filename):
    mis = lambda x: x.P
    net = Parser().parse(filename)
    mis1 = sum(map(mis, net.loads)) - sum(map(mis, net.generators))
    NR().solve_dc(net)
    mis2 = sum(map(mis, net.loads)) - sum(map(mis, net.generators))
    
    assert abs(mis1) >= abs(mis2)
