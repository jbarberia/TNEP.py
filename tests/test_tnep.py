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
    parameters = Parameters()
    parameters.read_excel(data_path + 'test_3.xlsx')

    model = TNEP()
    nets_solved, resultado = model.solve(nets, parameters)

    for net in nets_solved:
        assert len(net.branches) == 3


def test_basic_ens():
    """
    To debug the problem with ens
    """
    # Get cases
    parser = Parser()
    cases = [data_path + i for i in ['test_3_max.raw', 'test_3_min.raw']]
    nets = list(map(parser.parse, cases))
    
    # Get parameters
    parameters = Parameters()
    parameters.read_excel(data_path + 'test_3_ens.xlsx')

    model = TNEP()
    model.options['ens'] = 1e2
    nets_solved, resultado = model.solve(nets, parameters)

    for net in nets_solved:
        assert len(net.branches) == 2

    load_p = sum([sum(l.P for l in net.loads) for net in nets])
    load_p_solved = sum([sum(l.P for l in net.loads) for net in nets_solved])

    assert load_p - load_p_solved - resultado['r_dem'] <= 1e-2


def test_tnep_solution():
    """
    Para verificar la solucion,
    La sobrecarga maxima que sea menor al 105%
    """
    # Get cases
    parser = Parser()
    cases = [data_path + i for i in ['test_3_max.raw', 'test_3_min.raw']]
    nets = list(map(parser.parse, cases))
    for net in nets:
        NR().solve_ac(net)
    
    # Get parameters
    parameters = Parameters()
    parameters.read_excel(data_path + 'test_3.xlsx')

    model = TNEP()
    nets_solved, resultado = model.solve(nets, parameters)

    for net in nets_solved:
        NR().solve_dc(net)

    dfs = list(map(Reports().branches, nets_solved))
    max_per_case = [max(df['Carga %']) for df in dfs]

    assert max(max_per_case) <= 105.0


def test_96():
    parser = Parser()
    cases = [data_path + f"RTS-96-{i}.raw" for i in range(1, 6)]
    nets = list(map(parser.parse, cases))

    [br for net in nets for br in net.branches if br.in_service == False]

    for net in nets:
        NR().solve_dc(net)

    dfs = list(map(Reports().branches, nets))
    
    # Get parameters
    parameters = Parameters()
    parameters.read_excel(data_path + 'RTS-96.xlsx')

    model = TNEP()
    model.options['ens'] = 1e6
    model.options['penalty'] = 5e2
    model.options['rate factor'] = 0.7
    nets_solved, resultado = model.solve(nets, parameters)

    assert resultado["br_builded"] == 4


def test_mendoza():
    """
    To debug the problem
    """
    # Get cases
    parser = Parser()
    cases = [data_path + 'Mendoza.raw']
    nets = list(map(parser.parse, cases))
    
    # Get parameters
    parameters = Parameters()
    parameters.read_excel(data_path + 'Mendoza.xlsx')

    # Solve model
    model = TNEP()
    nets_solved, results = model.solve(nets, parameters)

    assert(results['status'] == 1)