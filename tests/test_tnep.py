import os
from tnep import Reports, NR
from tnep import Parser, TNEP, Parameters

data_path = os.path.dirname(os.path.realpath(__file__)) + '\\data\\'

def test_basic():
    """
    To debug the problem
    """
    # Get cases
    parser = Parser()
    cases = [data_path + i for i in ['test_3_max.raw', 'test_3_min.raw']]
    nets = list(map(parser.parse, cases))
    
    # Get parameters
    df_param = Parameters().read_excel(data_path + 'test_3.xlsx')

    model = TNEP()
    nets_solved = model.solve(nets, df_param)

    for net in nets_solved:
        assert len(net.branches) == 3


def test_tnep_solution():
    """
    To verify the solution
    """
    # Get cases
    parser = Parser()
    cases = [data_path + i for i in ['test_3_max.raw', 'test_3_min.raw']]
    nets = list(map(parser.parse, cases))
    for net in nets:
        NR().solve_ac(net)
    
    # Get parameters
    df_param = Parameters().read_excel(data_path + 'test_3.xlsx')

    model = TNEP()
    nets = model.solve(nets, df_param)

    for net in nets:
        NR().solve_dc(net)

    dfs = list(map(Reports().branches, nets))
    
    for df in dfs:
        print(df)

    max_per_case = [max(df['Carga %']) for df in dfs]

    parser.write('foo.raw', nets[0])#    zip(nets, ['foo1', 'foo2']))

    assert max(max_per_case) <= 105.0




