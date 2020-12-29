import optalg
import pfnet
from optmod import Problem, EmptyObjective

class NR():
    """
    Resolucion de flujos de potencia
    """
    def __init__(self):
        pass


    def solve_ac(self, net: pfnet.Network):
        """
        Resuelve un flujo de potencia de forma ac
        """
        
        net.clear_flags()

        # bus voltage angles
        net.set_flags('bus',
                    'variable',
                    'not slack',
                    'voltage angle')
        
        # bus voltage magnitudes
        net.set_flags('bus',
                    'variable',
                    'not regulated by generator',
                    'voltage magnitude')
        
        # slack gens active powers
        net.set_flags('generator',
                    'variable',
                    'slack',
                    'active power')
        
        # regulator gens reactive powers
        net.set_flags('generator',
                    'variable',
                    'regulator',
                    'reactive power')
        
        p = pfnet.Problem(net)
        p.add_constraint(pfnet.Constraint('AC power balance', net))  
        p.add_constraint(pfnet.Constraint('generator active power participation', net))
        p.add_constraint(pfnet.Constraint('PVPQ switching', net))
        p.add_heuristic(pfnet.Heuristic('PVPQ switching', net))
        p.analyze()

        self.solve(p, net)


    def solve_dc(self, net: pfnet.Network):
        """
        Resuelve un flujo de potencia de forma dc
        """
        
        net.clear_flags()

        # bus voltage angles
        net.set_flags('bus',
                    'variable',
                    'not slack',
                    'voltage angle')
            
        # slack gens active powers
        net.set_flags('generator',
                    'variable',
                    'slack',
                    'active power')
            
        p = pfnet.Problem(net)
        p.add_constraint(pfnet.Constraint('DC power balance', net))  
        p.add_constraint(pfnet.Constraint('generator active power participation', net))
        
        self.solve(p, net)
    
    def solve(self, problem, net):
        problem.analyze()

        solver = optalg.opt_solver.OptSolverNR()
        solver.set_parameters({'tol': 1e-4})
        solver.solve(problem)

        net.set_var_values(solver.get_primal_variables())
        net.update_properties()