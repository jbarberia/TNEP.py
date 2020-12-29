import pytest
from data import cases
from tnep import Parser, Reports


@pytest.mark.parametrize('filename', cases)
def test_bus_reports(filename):
    net = Parser().parse(filename)
    df = Reports().buses(net)

    assert len(net.buses) == len(df.axes[0])

@pytest.mark.parametrize('filename', cases)
def test_gen_reports(filename):
    net = Parser().parse(filename)
    df = Reports().generators(net)

    assert len(net.generators) == len(df.axes[0])

@pytest.mark.parametrize('filename', cases)
def test_br_reports(filename):
    net = Parser().parse(filename)
    df = Reports().branches(net)

    assert len(net.branches) == len(df.axes[0])