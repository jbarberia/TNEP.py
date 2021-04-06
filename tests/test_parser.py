import os
import pytest
import pfnet
from data import cases
from tnep import Parser
from unittest import TestCase

@pytest.mark.parametrize('filename', cases)
def test_parser_read(filename):
    net = Parser().parse(filename)
    
    assert isinstance(net, pfnet.Network)

# Skip Mendoza and RTS because of SW shunts aproximation
@pytest.mark.parametrize('filename', [case for case in cases if not ('RTS' in case or 'Mendoza' in case)])
def test_parser_write(filename):
    parser = Parser()
    net1 = parser.parse(filename)
    
    parser.write('tmp.raw', net1)
    net2 = parser.parse('tmp.raw')
    
    pfnet.tests.compare_networks(TestCase(), net1, net2)
    os.remove('tmp.raw')

def test_parser_read_multiple():
    parser = Parser()
    nets = list(map(parser.parse, cases))
    
    assert len(nets) == len(cases)
    