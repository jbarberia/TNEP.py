import os
import pytest
import pfnet
from unittest import TestCase
from tnep import Parser

data_path = os.path.dirname(os.path.realpath(__file__)) + '\\data'
data = [data_path + '\\' + case for case in os.listdir(data_path)]

@pytest.mark.parametrize('filename', data)
def test_parser_read(filename):
    net = Parser().parse(filename)
    
    assert isinstance(net, pfnet.Network)

@pytest.mark.parametrize('filename', data)
def test_parser_write(filename):
    parser = Parser()
    net1 = parser.parse(filename)
    
    parser.write('tmp.raw', net1)
    net2 = parser.parse('tmp.raw')
    
    pfnet.tests.compare_networks(TestCase(), net1, net2)
    os.remove('tmp.raw')

def test_parser_read_multiple():
    parser = Parser()
    nets = list(map(parser.parse, data))
    
    assert len(nets) == len(data)