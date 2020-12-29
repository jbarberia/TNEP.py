import pfnet
import numpy as np
import pandas as pd
from optalg.opt_solver import OptSolverCbcCMD
from optmod import VariableDict, Problem, minimize


class TNEP():
    """
    Class to solve TNEP
    """

    def __init__(self):
        pass

    def solve(self, nets, parameters: pd.DataFrame):
        """
        Resuelve el TNEP, devuelve un listado de PFNET Networks
        con la solucion
        """

        # Pre-Proceso del caso
        scenarios = self.copy_networks(nets)
        self.create_branches(scenarios, parameters)
        self.create_rating(scenarios)

        # Indices
        bus_indices = []
        gen_indices = []
        br_indices = []
        br_indices_oos = []
        for i, net in scenarios.items():
            bus_indices.extend([(bus.index, i) for bus in net.buses])
            gen_indices.extend([(gen.index, i) for gen in net.generators if gen.is_slack])
            br_indices.extend([(br.index, i) for br in net.branches])
            br_indices_oos.extend([(bus.index, i) for br in net.branches if not br.is_in_service()]) # TODO: better independent of scenario

        # Variables
        w = VariableDict(bus_indices, name='w')
        r = VariableDict(bus_indices, name='r')
        pg = VariableDict(gen_indices, name='pg')
        f = VariableDict(br_indices, name='f')
        f_ = VariableDict(br_indices, name='vio')
        phi_ = VariableDict(br_indices_oos, name='phi')
        x = VariableDict([i for i, _ in br_indices_oos], name='x')

        # Objective
        # TODO: Deberia summarse un par de variables
        C1 = 1e3
        C2 = 1e3

        phi = 0
        # Costo de Linea
        for i, x_var in x.values():
            phi += parameters[index == i] * x_var
        # Exceso del limite termico
        for violation in f_.values():
            phi += violation * C1
        # Recorte de demanda
        for r_shed in r.values():
            phi += r_shed * C2

        # Constraints
        constraints = []
        for i, net in scenarios.items():
            
            # Power Balance
            for bus in net.buses:
                if bus.is_slack():
                    constraints.append(w[bus.index, i] == 0.)
                dp = r[bus.index, i]
                for gen in bus.generators:
                    dp += pg[gen.index, i] if gen.is_slack() else gen.P
                for load in bus.loads:
                    dp -= load.P
                for br in bus.branches_k:
                    dp -= f[br.index, i]
                for br in bus.branches_m: 
                    dp += f[br.index, i]
                constraints.extend([
                    dp == 0.,
                    r[bus.index, i] >= 0.
                ])

            # Dinamics in branches
            for br in net.branches:
                ckt = br.index
                k, m = br.bus_k.index, br.bus_m.index

                rate = br.get_rating('A') # TODO: Estaria bueno que se puedan usar los limites A, B, C

                if not br.is_in_service(): # O sino con los indices
                    M = 1e2 # big M
                    constraints.extend([
                        f[ckt, i] + br.b*(w[k, i] - w[m, i]) <= (1 - x[ckt])*M,
                        f[ckt, i] + br.b*(w[k, i] - w[m, i]) >= -(1 - x[ckt])*M,

                        f[ckt, i] <= x[ckt] * rate + phi_[ckt, i],
                        f[ckt, i] >= -x[ckt] * rate - phi_[ckt, i],

                        phi_[ckt, i] - f_[ckt, i] <= (1 - x[ckt])*M,
                        phi_[ckt, i] - f_[ckt, i] >= -(1 - x[ckt])*M,

                        phi_[ckt, i] <= x[ckt]*M,
                        phi_[ckt, i] >= -x[ckt]*M
                    ])

                else:
                    constraints.extend([
                        f[ckt, i] == br.b*(w[k, i] - w[m, i]),
                        f[ckt, i] <= rate + f_[ckt, i],
                        f[ckt, i] >= -rate - f_[ckt, i]
                    ])

                constraints.extend([
                    f_[ckt, i] >= 0.
                ])

            # Limits in slack gens
            for gen in net.generators:
                if gen.is_slack():
                    constraints.extend([
                        pg[gen.index, i] <= gen.P_max,
                        pg[gen.index, i] >= gen.P_min
                    ])

        p = Problem(minimize(phi), constraints)
        p.solve(solver=OptSolverCbcCMD(), parameters={'quiet': False})

        # Update networks
        # TODO complete it
        
        return NotImplemented 

    def copy_networks(self, nets):
        """
        Devuelve un diccionario numerado con
        la copia de las PFNET Networks
        """
        copy_nets = {i: net.get_copy() for i, net in enumerate(nets)}
        return copy_nets


    def create_branches(self, nets, parameters: pd.DataFrame):
        """
        Crea las ramas y las suma a cada PFNET Networks
        nets: Diccionario con PFNET Networks
        parameters: DataFrame con los datos de las lineas
        """

        for net in nets.values():
            new_branches = []
            for index, row in parameters.iterrows():
                new_br = pfnet.Branch()
                new_br.in_service = False

                new_br.bus_k = net.get_bus_from_number(row['Bus k'])
                new_br.bus_m = net.get_bus_from_number(row['Bus m'])

                den = row['x']**2 + row['r']**2
                new_br.g = row['r'] / den
                new_br.b = -row['x'] / den

                new_br.b_k = new_br.b_m = row['b'] / 2
                new_branches.append(new_br)

            net.add_branches(new_branches)
            net.update_properties()

    def create_rating(self, nets):
        """
        Impone un limite termico razonable
        a cada linea que no tiene rating
        """

        for net in nets.values():
            for br in net.branches:
                if br.get_rating('A') <= 0.:
                    delta_max = np.deg2rad(30)
                    br.ratingA = np.sin(delta_max) * br.b