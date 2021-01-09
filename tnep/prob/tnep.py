import pfnet
import numpy as np
import pandas as pd
from pulp import LpProblem, LpVariable, LpMinimize, value, PULP_CBC_CMD


class TNEP():
    """
    Class to solve TNEP
    """

    def __init__(self):
        pass

    def solve(self, nets, parameters: pd.DataFrame, rate_factor=1., penalty=1e3, ens=1e3):
        """
        Resuelve el TNEP, devuelve un listado de PFNET Networks
        con la solucion
        """

        # Pre-Proceso del caso
        scenarios, to_build_table = self.copy_networks(nets) # TODO retornar hash table con ckt existentes
        candidates, to_build_table = self.create_branches(scenarios, parameters, to_build_table) # TODO modificar hashtable
        self.create_rating(scenarios)

        # Indices
        bus_indices = []
        load_bus_indices = []
        gen_indices = []
        br_indices = [idx for idx, to_build in to_build_table.items()]
        br_indices_to_build = [idx for idx, to_build in to_build_table.items() if to_build]
        for i, net in scenarios.items():
            bus_indices.extend([(bus.number, i) for bus in net.buses])
            load_bus_indices.extend([(bus.number, i) for bus in net.buses if len(bus.loads) > 0])
            gen_indices.extend([(gen.index, i) for gen in net.generators if gen.is_slack])

        br_indices_oos = list(candidates['index'])

        # Instaciate problem
        prob = LpProblem("TLEP", LpMinimize)

        # Variables
        w = {(idx, i): LpVariable(f'w_{idx}_{i}') for (idx, i) in bus_indices}
        pg = {(idx, i): LpVariable(f'pg_{idx}_{i}') for (idx, i) in gen_indices}
        f = {(idx): LpVariable(f'f_{idx}') for (idx) in br_indices}
        f_ = {(idx): LpVariable(f'vio_{idx}', lowBound=0.) for idx in br_indices}
        phi_ = {(idx): LpVariable(f'phi_{idx}', lowBound=0.) for idx in br_indices_to_build}

        r = {(idx, i): LpVariable(f'r_{idx}_{i}', lowBound=0.) for (idx, i) in load_bus_indices}
        x = {(k, m, name): LpVariable(
                f'x_{k, m, name}',
                cat='Integer',
                lowBound=0,
                upBound=1) 
                for (k, m, name, i) in br_indices_to_build}
        
        # Objective
        prob += (sum(c * x[idx] for idx, c in zip(candidates['index'], candidates['Costo'])) 
                 + penalty * sum(vio for vio in f_.values())
                 + ens * sum(l_shed for l_shed in r.values()))

        # Constraints
        for i, net in scenarios.items():
            for bus in net.buses: # Power Balance
                dp = 0.0
                for gen in bus.generators:
                    dp += pg[gen.index, i] if gen.is_slack() else gen.P
                for load in bus.loads:
                    dp -= load.P
                    dp += r[bus.number, i] # Recorte de carga
                for br in bus.branches_k:
                    ckt = (br.bus_k.number, br.bus_m.number, br.name, i)
                    dp -= f[ckt]
                for br in bus.branches_m:
                    ckt = (br.bus_k.number, br.bus_m.number, br.name, i)
                    dp += f[ckt]
                prob += dp == 0

            for br in net.branches:
                k, m, name = br.bus_k.number, br.bus_m.number, br.name
                ckt = (k, m, name, i)

                rate = br.get_rating('A') * rate_factor
                
                # Ecuaciones de flujo
                if br.is_in_service():
                    prob += f[ckt] == -br.b*(w[k, i]-w[m, i])
                    prob += f[ckt] <= rate + f_[ckt]
                    prob += f[ckt] >= -rate - f_[ckt]

                if not br.is_in_service():
                    M = 1e2
                    prob += f[ckt]+br.b*(w[k, i]-w[m, i])<= (1-x[k, m, name])*M
                    prob += f[ckt]+br.b*(w[k, i]-w[m, i])>= -(1-x[k, m, name])*M

                    prob += f[ckt] <= x[k, m, name]*rate + phi_[ckt]
                    prob += f[ckt] >= -x[k, m, name]*rate - phi_[ckt]

                    prob += phi_[ckt] - f_[ckt] <= (1-x[k, m, name])*M
                    prob += phi_[ckt] - f_[ckt] >= -(1-x[k, m, name])*M
                    
                    prob += phi_[ckt] <= x[k, m, name]*M
                    prob += phi_[ckt] >= -x[k, m, name]*M
                
            for bus in net.buses:
                if bus.is_slack():
                    prob += w[bus.number, i] == 0.

            for gen in net.generators:
                if gen.is_slack():
                    prob += pg[gen.index, i] <= gen.P_max
                    prob += pg[gen.index, i] >= gen.P_min

        # Solve
        prob.solve(
            PULP_CBC_CMD(
                mip=True,
                cuts=True,
                msg=0,
                warmStart=True,
                presolve=False
                )
            )

        # Update Branches in Network
        for (k, m, name), build in x.items():
            for net in scenarios.values():
                br = net.get_branch_from_name_and_bus_numbers(name, k, m)
                if build.varValue == True:
                    br.in_service = True
                else:
                    br.in_service = False

        # Delete branches OOS
        for net in scenarios.values():
            br_to_remove = []
            for br in net.branches:
                if not br.is_in_service():
                    br_to_remove.append(br)
            net.remove_branches(br_to_remove)

        # Update Vars in Network
        for i, net in scenarios.items():
            for bus in net.buses:
                bus.v_ang = w[bus.number, i].varValue

            for gen in net.generators:
                if gen.is_slack():
                    gen.P = pg[gen.index, i].varValue

        return list(scenarios.values()), 

    def copy_networks(self, nets):
        """
        Devuelve un diccionario numerado con
        la copia de las PFNET Networks

        Devuelve un hashtable con las lineas existentes
        """
        copy_nets = {i: net.get_copy() for i, net in enumerate(nets)}

        to_build_table = {}
        for i, net in copy_nets.items():
            for br in net.branches:
                to_build_table[br.bus_k.number, br.bus_m.number, br.name, i] = False

        return copy_nets, to_build_table


    def create_branches(self, nets, parameters: pd.DataFrame, to_build_table):
        """
        Crea las ramas y las suma a cada PFNET Networks
        nets: Diccionario con PFNET Networks
        parameters: DataFrame con los datos de las lineas
        """

        for i, net in nets.items():
            parameters['index'] = [(k, m, 'NL') for k, m in zip(parameters['Bus k'], parameters['Bus m'])]
            new_branches = []            
            for index, row in parameters.iterrows():
                new_br = pfnet.Branch()
                new_br.bus_k = net.get_bus_from_number(row['Bus k'])
                new_br.bus_m = net.get_bus_from_number(row['Bus m'])
                new_br.name = 'NL'
                den = row['x']**2 + row['r']**2
                new_br.g = row['r'] / den
                new_br.b = -row['x'] / den
                new_br.b_k = new_br.b_m = row['b'] / 2
                new_br.ratingA = row['Rating']/net.base_power
                new_br.in_service = False
                new_branches.append(new_br)

            net.add_branches(new_branches)
            net.update_properties()

            for br in net.branches:
                if to_build_table.get((br.bus_k.number, br.bus_m.number, br.name, i), True):
                    to_build_table[br.bus_k.number, br.bus_m.number, br.name, i] = True

        return parameters, to_build_table

    def create_rating(self, nets):
        """
        Impone un limite termico razonable
        a cada linea que no tiene rating
        """

        for net in nets.values():
            for br in net.branches:
                if br.get_rating('A') <= 0.:
                    delta_max = np.deg2rad(30)
                    br.ratingA = abs(np.sin(delta_max) * br.b)