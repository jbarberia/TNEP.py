import os
import pytest
import pandas as pd
from data import parameters
from tnep import Parameters

def test_generate_templates():
    parameters = Parameters()
    parameters.generate_template('tmp.xlsx')
    parameters.read_excel('tmp.xlsx')

    default_col = set(['Bus k', 'Bus m', 'id', 'r', 'x', 'b', 'Rating', 'Costo'])

    assert default_col <= set(parameters.candidates.columns)

    os.remove('tmp.xlsx')

@pytest.mark.parametrize('filename', parameters)
def test_parameters(filename):
    parameters = Parameters()
    parameters.read_excel(filename)

    assert isinstance(parameters.candidates, pd.DataFrame)
    assert isinstance(parameters.monitored, pd.DataFrame)

