import os
import pytest
import pandas as pd
from data import parameters
from tnep import Parameters

def test_generate_templates():
    parameters = Parameters()
    parameters.generate_template('tmp.xlsx')
    parameters.read_excel('tmp.xlsx')

    default_col = set(['Bus k', 'Bus m', 'r', 'x', 'b', 'Rating', 'Cost'])

    assert default_col <= set(parameters.data.columns)

    os.remove('tmp.xlsx')

@pytest.mark.parametrize('filename', parameters)
def test_parameters(filename):
    df_param = Parameters().read_excel(filename)

    assert isinstance(df_param, pd.DataFrame)

