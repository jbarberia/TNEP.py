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
        scenarios = self.copy_networks(nets)
        candidates = self.create_branches(scenarios, parameters) # Se suma col index
        self.create_rating(scenarios)

        # Indices
        bus_indices = []
        load_bus_indices = []
        gen_indices = []
        br_indices = []
        # br_indices_to_build = []
        for i, net in scenarios.items():
            bus_indices.extend([(bus.index, i) for bus in net.buses])
            load_bus_indices.extend([(bus.index, i) for bus in net.buses if len(bus.loads) > 0])
            gen_indices.extend([(gen.index, i) for gen in net.generators if gen.is_slack])
            br_indices.extend([(br.index, i) for br in net.branches])
            # br_indices.extend([(br.bus_k.index, br.bus_m.index, br.name, i) for br in net.branches])
            # br_indices_to_build.extend([(br.bus_k.index, br.bus_m.index, br.name, i) for br in net.branches if br.to_build])

        br_indices_oos = list(candidates['index'])

        # Instaciate problem
        prob = LpProblem("TLEP", LpMinimize)

        # Variables
        w = {(idx, i): LpVariable(f'w_{idx}_{i}') for (idx, i) in bus_indices}
        pg = {(idx, i): LpVariable(f'pg_{idx}_{i}') for (idx, i) in gen_indices}
        f = {(idx, i): LpVariable(f'f_{idx}_{i}') for (idx, i) in br_indices}
        f_ = {(idx, i): LpVariable(f'vio_{idx}_{i}', lowBound=0.) 
                                for idx, i in br_indices}
        phi_ = {(br.index, i): LpVariable(f'phi_{br.index}_{i}', lowBound=0.) 
                                  for (i, net) in scenarios.items()
                                  for br in net.branches
                                  if not br.is_in_service()}
        # phi_ = {(idx, i): LpVariable(f'phi_{br.index}_{i}', lowBound=0.) for (idx, i) in br_indices_to_build}

        r = {(idx, i): LpVariable(f'r_{idx}_{i}', lowBound=0.) for (idx, i) in load_bus_indices}
        x = {i: LpVariable(
                f'x_{i}',
                cat='Integer',
                lowBound=0,
                upBound=1) 
                for i in br_indices_oos}
               # for i in br_indices_to_build}
        
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
                    dp += r[bus.index, i] # Recorte de carga
                for br in bus.branches_k:
                    ckt = br.index
                    dp -= f[ckt, i]
                for br in bus.branches_m:
                    ckt = br.index
                    dp += f[ckt, i]
                prob += dp == 0

            for br in net.branches:
                ckt = br.index
                k, m = br.bus_k.index, br.bus_m.index

                # id = br.name
                # ckt = (k, m, id)

                rate = br.get_rating('A') * rate_factor
                
                # Ecuaciones de flujo
                if br.is_in_service():
                    prob += f[ckt, i] == -br.b*(w[k, i]-w[m, i])
                    prob += f[ckt, i] <= rate + f_[ckt,i]
                    prob += f[ckt, i] >= -rate - f_[ckt,i]

                if not br.is_in_service():
                    M = 1e2
                    prob += f[ckt, i]+br.b*(w[k, i]-w[m, i])<= (1-x[ckt])*M
                    prob += f[ckt, i]+br.b*(w[k, i]-w[m, i])>= -(1-x[ckt])*M

                    prob += f[ckt, i] <= x[ckt]*rate + phi_[ckt, i]
                    prob += f[ckt, i] >= -x[ckt]*rate - phi_[ckt, i]

                    prob += phi_[ckt, i] - f_[ckt, i] <= (1-x[ckt])*M
                    prob += phi_[ckt, i] - f_[ckt, i] >= -(1-x[ckt])*M
                    
                    prob += phi_[ckt, i] <= x[ckt]*M
                    prob += phi_[ckt, i] >= -x[ckt]*M
                
            for bus in net.buses:
                if bus.is_slack():
                    prob += w[bus.index, i] == 0.

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
        for k, build in x.items():
            if build.varValue == True:
                for net in scenarios.values():
                    br = net.get_branch(k)
                    br.in_service = True

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
                bus.v_ang = w[bus.index, i].varValue

            for gen in net.generators:
                if gen.is_slack():
                    gen.P = pg[gen.index, i].varValue

        return list(scenarios.values())

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
        # TODO: add to_build attribute 

        for net in nets.values():
            start_idx = stop_idx = len(net.branches)
            stop_idx += len(parameters)
            parameters['index'] = list(range(start_idx, stop_idx))

            new_branches = []            
            for index, row in parameters.iterrows():
                new_br = pfnet.Branch()
                new_br.bus_k = net.get_bus_from_number(row['Bus k'])
                new_br.bus_m = net.get_bus_from_number(row['Bus m'])
                den = row['x']**2 + row['r']**2
                new_br.g = row['r'] / den
                new_br.b = -row['x'] / den
                new_br.b_k = new_br.b_m = row['b'] / 2
                new_br.ratingA = row['Rating']/net.base_power
                new_br.in_service = False
                new_branches.append(new_br)

            net.add_branches(new_branches)
            net.update_properties()

        return parameters

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