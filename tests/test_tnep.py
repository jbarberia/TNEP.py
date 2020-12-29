import os   
from tnep import Parser, TNEP, Parameters

data_path = os.path.dirname(os.path.realpath(__file__)) + '\\data\\'

def test_tnep():

    # Get cases
    parser = Parser()
    cases = [data_path + i for i in ['test_3_max.raw', 'test_3_min.raw']]
    nets = list(map(parser.parse, cases))
    
    # Get parameters
    df_param = Parameters().read_excel(data_path + 'test_3.xlsx')

    model = TNEP()
    nets = model.solve(nets, df_param)

    assert len(nets[0]) == 3