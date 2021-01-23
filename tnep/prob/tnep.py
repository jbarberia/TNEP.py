import pfnet
import numpy as np
import pandas as pd
from copy import deepcopy
from pulp import LpProblem, LpVariable, LpMinimize, value, PULP_CBC_CMD


class TNEP():
    """
    Class to solve TNEP
    """

    def __init__(self):
        pass

    def solve(self, nets, parameters, rate_factor=0.8, penalty=2e3, ens=1e4):
        """
        Resuelve el TNEP, devuelve un listado de PFNET Networks
        con la solucion

        parameters es un objeto del tipo Parameters
        """

        # Create useful data structure
        ds = self._create_data_structure(nets, parameters)

        # Instanciate problem
        prob = LpProblem("TLEP", LpMinimize)

        # Variables
        w = {(i, bus_i): LpVariable(f'w_{i}_{bus_i}') for (i, bus_i) in ds["ref"]["bus"]}
        pg = {(i, bus_i, name): LpVariable(f'ps_{i}_{bus_i}_{name}') for (i, bus_i, name) in ds["ref"]["gen"]}
        f = {(i, k, m, ckt): LpVariable(f'f_{i, k, m, ckt}') for (i, k, m, ckt) in ds["ref"]["arcs"]}
        f_ = {(i, k, m, ckt): LpVariable(f'f_vio_{i, k, m, ckt}') for (i, k, m, ckt) in list(set(ds["ref"]["ne_arcs"] + ds["ref"]["mo_arcs"]))}
        phi_ = {(i, k, m, ckt): LpVariable(f'phi_{i, k, m, ckt}') for (i, k, m, ckt) in ds["ref"]["ne_arcs"]}
        x = {(k, m, ckt): LpVariable(f'x{k, m, ckt}', cat='Integer', lowBound=0, upBound=1) for (k, m, ckt) in ds["ref"]["ne_arc"]}

        #r = {(idx, i): LpVariable(f'r_{idx}_{i}', lowBound=0.) for (idx, i) in load_bus_indices} POR EL MOMENTO NO SE TIENE EN CUENTA

        # Objective
        prob += (sum(arc['cost'] * x[index] for (index, arc) in ds["ne_br"].items()) 
                 + penalty * sum(vio for vio in f_.values()))
                 #+ ens * sum(l_shed for l_shed in r.values()))

        # Constraints
        for i, net in ds["nets"].items():
            for bus in net.buses: # Power Balance
                dp = 0.0

                for gen in bus.generators:
                    dp += pg[i, bus.number, gen.name] if bus.is_slack() else gen.P

                for load in bus.loads:
                    dp -= load.P

                for (j, k, m, ckt) in ds["ref"]["arcs"]: # Arcs es la union de lineas + lineas candidatos
                    if j == i:
                        if k == bus.number:
                            dp -= f[i, k, m, ckt]
                        if m == bus.number:
                            dp += f[i, k, m, ckt]

                prob += dp == 0

            for br in net.branches: # Lineas comunes y a monitorear
                k, m, ckt = br.bus_k.number, br.bus_m.number, br.name
                prob += f[i, k, m, ckt] == -br.b*(w[i, k]-w[i, m])
            
            for bus in net.buses:
                if bus.is_slack():
                    prob += w[i, bus.number] == 0.

        for (i, k, m, ckt) in ds["ref"]["mo_arcs"]:
            rate = ds["mo_br"][(k, m, ckt)]['rate'] * rate_factor
            prob += f[i, k, m, ckt] <= rate + f_[i, k, m, ckt]
            prob += f[i, k, m, ckt] >= -rate - f_[i, k, m, ckt]
            prob += f_[i, k, m, ckt] >= 0
            prob += f_[i, k, m, ckt] <= 1.5
                

        for (i, k, m, ckt) in ds["ref"]["ne_arcs"]:
            br = ds["ne_br"][(k, m, ckt)]['br']
            rate = ds["ne_br"][(k, m, ckt)]['rate'] * rate_factor

            M = 1e3
            prob += f[i, k, m, ckt]+br.b*(w[i, k]-w[i, m]) <= (1-x[k, m, ckt])*M
            prob += f[i, k, m, ckt]+br.b*(w[i, k]-w[i, m]) >= -(1-x[k, m, ckt])*M

            prob += f[i, k, m, ckt] <= rate + f_[i, k, m, ckt]
            prob += f[i, k, m, ckt] >= -rate - f_[i, k, m, ckt]

            prob += f[i, k, m, ckt] <= x[k, m, ckt]*rate + phi_[i, k, m, ckt]
            prob += f[i, k, m, ckt] >= -x[k, m, ckt]*rate - phi_[i, k, m, ckt]

            prob += phi_[i, k, m, ckt] - f_[i, k, m, ckt] <= (1-x[k, m, ckt])*M
            prob += phi_[i, k, m, ckt] - f_[i, k, m, ckt] >= -(1-x[k, m, ckt])*M

            prob += phi_[i, k, m, ckt] <= x[k, m, ckt]*M
            prob += phi_[i, k, m, ckt] >= -x[k, m, ckt]*M
            prob += f_[i, k, m, ckt] >= 0

        prob.solve(
            PULP_CBC_CMD(
                mip=True,
                cuts=True,
                msg=1,
                options=['barrier'],
                presolve=True,
                )
            )
        

        # Get solution details
        ds["solution"] = {
            'objective': prob.objective.value(),
            'br_builded': sum(var.value() for var in x.values()),
            'br_cost': sum(x[index].value() * br['cost'] for (index, br) in ds["ne_br"].items()),
            'status': prob.status
        }

        # Update Branches in Network

        for net in ds["nets"].values():
            build_branches = []
            for (k, m, ckt), build in x.items():
                if round(build.value()) > 0:
                    ref_br = (ds["ne_br"][(k, m, ckt)]['br'])
                    br = pfnet.Branch()
                    br.bus_k = net.get_bus_from_number(k)
                    br.bus_m = net.get_bus_from_number(m)
                    br.name = ref_br.name
                    br.g = ref_br.g
                    br.b = ref_br.b
                    br.ratingA = ref_br.ratingA
                    br.in_service = br.in_service
                    build_branches.append(br)

            net.add_branches(build_branches)
            net.update_properties()
        
        return list(ds["nets"].values()), ds["solution"]


    def _create_data_structure(self, nets, parameters):

        ds = {}
        ds["nets"] = {i: net.get_copy() for i, net in enumerate(nets)}

        # strip whitespaces in branches for easy handling of data
        for (i, net) in ds["nets"].items():
            for br in net.branches:
                br.name = br.name.strip()

        ds["mo_br"] = {}
        for (_, row) in parameters.monitored.iterrows():
            k, m = int(row['Bus k']), int(row['Bus m'])
            try:
                ckt = str(int(row['id']))
            except ValueError:
                ckt = str(row['id'])
            rate = row['Rating'] / net.base_power
            ds["mo_br"][k, m, ckt] = {'rate': rate}
        
        ds["ne_br"] = {}
        for (_, row) in parameters.candidates.iterrows():
            k, m = int(row['Bus k']), int(row['Bus m']) 
            try:
                ckt = str(int(row['id']))
            except ValueError:
                ckt = str(row['id'])
            rate = row['Rating'] / net.base_power
            br = pfnet.Branch()
            br.name = ckt
            den = row['x']**2 + row['r']**2
            br.g = row['r'] / den
            br.b = -row['x'] / den
            br.b_k = br.b_m = row['b'] / 2
            br.ratingA = rate
            br.in_service = True
            ds["ne_br"][k, m, ckt] = {'br': br, 'cost': row['Costo'], 'rate': rate}

        # Build indices
        ds["ref"] = {
            "bus": [],
            "gen": [],
            "arcs": [],
            "mo_arcs": [],
            "ne_arcs": []
        }

        br_indices = []
        for (i, net) in ds["nets"].items():
            for bus in net.buses:
                ds["ref"]["bus"].append((i, bus.number))

                if bus.is_slack():
                    for gen in bus.generators:
                        ds["ref"]["gen"].append((i, bus.number, gen.name))

            for br in net.branches:
                k, m, ckt = br.bus_k.number, br.bus_m.number, br.name
                br_indices.append((i, k, m ,ckt))

                if (k, m, ckt) in ds["mo_br"].keys():
                    ds["ref"]["mo_arcs"].append((i, k, m, ckt))

            for (k, m, ckt) in ds["ne_br"].keys():
                ds["ref"]["ne_arcs"].append((i, k, m, ckt))
                br_indices.append((i, k, m, ckt))

            ds["ref"]["ne_arc"] = list(ds["ne_br"].keys())
        ds["ref"]["arcs"] = list(set(br_indices)) # Remove duplicates

        return ds
        