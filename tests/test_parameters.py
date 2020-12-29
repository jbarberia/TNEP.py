import os
from tnep import Parameters

def test_generate_templates():
    parameters = Parameters()
    parameters.generate_template('tmp.xlsx')
    parameters.read_excel('tmp.xlsx')

    default_col = set(['Bus k', 'Bus m', 'r', 'x', 'b', 'Rating', 'Cost'])

    assert default_col <= set(parameters.data.columns)

    os.remove('tmp.xlsx')
