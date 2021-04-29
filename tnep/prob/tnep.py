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
        self.options = {
            'rate factor': 0.8,
            'penalty': 2e3,
            'ens': 2e3
        }

    def solve(self, nets, parameters):
        """
        Resuelve el TNEP, devuelve un listado de PFNET Networks
        con la solucion

        parameters es un objeto del tipo Parameters
        """
        options = self.options

        # Create useful data structure
        ds = self._create_data_structure(nets, parameters)

        # Instanciate problem
        prob = LpProblem("TLEP", LpMinimize)

        # Variables
        w = {(i, bus_i): LpVariable(f'w_{i}_{bus_i}') for (i, bus_i) in ds["ref"]["bus"]}
        r = {(i, bus_i): LpVariable(f'r_{i}_{bus_i}', lowBound=0) for (i, bus_i) in ds["ref"]["bus"]}
        pg = {(i, bus_i, name): LpVariable(f'ps_{i}_{bus_i}_{name}') for (i, bus_i, name) in ds["ref"]["gen"]}
        f = {(i, k, m, ckt): LpVariable(f'f_{i, k, m, ckt}') for (i, k, m, ckt) in ds["ref"]["arcs"]}
        f_ = {(i, k, m, ckt): LpVariable(f'f_vio_{i, k, m, ckt}') for (i, k, m, ckt) in list(set(ds["ref"]["ne_arcs"] + ds["ref"]["mo_arcs"]))}
        phi_ = {(i, k, m, ckt): LpVariable(f'phi_{i, k, m, ckt}') for (i, k, m, ckt) in ds["ref"]["ne_arcs"]}
        x = {(k, m, ckt): LpVariable(f'x{k, m, ckt}', cat='Integer', lowBound=0, upBound=1) for (k, m, ckt) in ds["ref"]["ne_arc"]}

        # Objective
        prob += (sum(arc['cost'] * x[index] for (index, arc) in ds["ne_br"].items()) 
                 + options['penalty'] * sum(vio for vio in f_.values())
                 + options['ens'] * sum(ds['c_k'][i[0]] * ds['crf'] * l_shed for i, l_shed in r.items()))

        # Constraints
        for i, net in ds["nets"].items():
            for bus in net.buses: # Power Balance
                if not bus.is_in_service():
                    continue
                dp = 0.0

                for gen in bus.generators:
                    dp += pg[i, bus.number, gen.name] if bus.is_slack() else gen.P

                # Recorte de carga  
                dp += r[i, bus.number]

                for load in bus.loads:
                    dp -= load.P

                # Se podria optimizar esta parte
                for (j, k, m, ckt) in ds["ref"]["arcs"]: # Arcs es la union de lineas + lineas candidatos
                    if j == i:
                        if k == bus.number:
                            dp -= f[i, k, m, ckt]
                        if m == bus.number:
                            dp += f[i, k, m, ckt]

                prob += dp == 0

            for br in net.branches: # Lineas comunes y a monitorear
                if not br.is_in_service():
                    continue
                k, m, ckt = br.bus_k.number, br.bus_m.number, br.name
                prob += f[i, k, m, ckt] == -br.b*(w[i, k]-w[i, m])
            
            for bus in net.buses:
                if not bus.is_in_service():
                    continue

                if bus.is_slack():
                    prob += w[i, bus.number] == 0.
                prob += r[i, bus.number] <= sum(load.P for load in bus.loads if load.is_in_service()) * ds['load bus'].get(bus.number, 0.)

        for (i, k, m, ckt) in ds["ref"]["mo_arcs"]:
            rate = ds["mo_br"][(k, m, ckt)]['rate'] * options['rate factor']
            prob += f[i, k, m, ckt] <= rate + f_[i, k, m, ckt]
            prob += f[i, k, m, ckt] >= -rate - f_[i, k, m, ckt]
            prob += f_[i, k, m, ckt] >= 0
            prob += f_[i, k, m, ckt] <= 1.5
                
        for (i, k, m, ckt) in ds["ref"]["ne_arcs"]:
            br = ds["ne_br"][(k, m, ckt)]['br']
            rate = ds["ne_br"][(k, m, ckt)]['rate'] * options['rate factor']

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
                cuts=False,
                msg=1,
                options=['preprocess off presolve on gomoryCuts on'],
                )
            )
        
        # Get solution details
        ds["solution"] = {
            'objective': prob.objective.value(),
            'br_builded': sum(var.value() for var in x.values()),
            'br_cost': sum(x[index].value() * br['cost'] for (index, br) in ds["ne_br"].items()),
            'overload': options['penalty'] * sum(vio.value() for vio in f_.values()),
            'r_dem': sum(var.value() for var in r.values()),
            'ens': options['ens'] * sum(ds['c_k'][i[0]] * ds['crf'] * l_shed.value() for i, l_shed in r.items()),
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

        # Update load shed
        for i, i_bus in r.keys():
            net = ds["nets"][i]
            bus = net.get_bus_from_number(i_bus)
            if sum(l.P for l in bus.loads) > 0:
                load = bus.loads[0]
                load.P = load.P - r[i, i_bus].value()
                load.update_P_components(1, 0, 0)
            net.update_properties()        
        
        return list(ds["nets"].values()), ds["solution"]


    def _create_data_structure(self, nets, parameters):

        ds = {}
        ds["nets"] = {i: net.get_copy() for i, net in enumerate(nets)}

        # ENS coefficient
        if not hasattr(self, "D_k"): self.D_k = [0] * len(ds["nets"])
        if not hasattr(self, "F_k"): self.F_k = [0] * len(ds["nets"])
        if not hasattr(self, "T_k"): self.T_k = [0] * len(ds["nets"])

        ds["c_k"] = {i: D*F*T/24 for i, (D, F, T) in enumerate(zip(self.D_k, self.F_k, self.T_k))}

        r = self.r if hasattr(self, "r") else 1
        n = self.n if hasattr(self, "n") else 0
        ds["crf"] = ((1+r)**n - 1)/(r*(1+r)**n)

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

        ds["load bus"] = {}
        for (_, row) in parameters.loads.iterrows():
            i = int(row['Bus'])
            percentage = float(row['Recorte Max'])
            ds["load bus"][i] = percentage

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
                if not bus.is_in_service():
                    continue
                ds["ref"]["bus"].append((i, bus.number))

                if bus.is_slack():
                    for gen in bus.generators:
                        ds["ref"]["gen"].append((i, bus.number, gen.name))

            for br in net.branches:
                if not br.is_in_service():
                    continue
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
        
