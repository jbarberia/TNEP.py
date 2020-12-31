import optalg
import pfnet
import numpy as np
import scipy.sparse as ss

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
        p.analyze()

        self.solve(p, net)
    
    def solve(self, problem, net, tol=1e-4, itr_max=25):
        
        x = problem.get_init_point()
        problem.eval(x)

        residual = lambda x: np.hstack((problem.A*x-problem.b, problem.f))
        k = 0
        while np.linalg.norm(residual(x)) > tol or k == itr_max:
            problem.apply_heuristics(x)
            A = ss.bmat([[problem.A],[problem.J]],format='csr')
            B = -residual(x)
            x = x + ss.linalg.spsolve(A, B)
            problem.eval(x)
            k += 1

        net.set_var_values(x)
        net.update_properties()