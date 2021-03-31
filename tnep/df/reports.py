import os
import pfnet
import numpy as np
import pandas as pd
from openpyxl import load_workbook

class Reports():
    """
    Generacion de reportes para ver estado del escenario
    """

    def __init__(self):
        pass

    def check_name(self, filename, ext_list: list):
        """
        Verifica que la extension sea .xlsx
        """
        name, ext = os.path.splitext(filename)
        if ext.lower() in ext_list:
            return filename
        else:
            raise ValueError('Invalid extension')


    def to_excel(self, df, filename, sheet="Sheet1"):
        """
        Escribe un excel con los reportes
        """
        filename = self.check_name(filename, ['.xlsx', '.xls'])
        xl = load_workbook(filename)

        writer = pd.ExcelWriter(filename, engine='openpyxl') 
        writer.book = xl

        df.to_excel(writer, sheet)
        writer.save()


    def to_html(self, df, filename):
        """
        Escribe un html con los reportes
        """
        filename = self.check_name(filename, '.html')

        df.to_html(filename)


    def buses(self, net: pfnet.Network):
        """
        Reporte de todas las barras
        """
        df = pd.DataFrame(columns=['Number', 'Name', 'V', '°', 'V Max', 'V Min'])
        for bus in reversed(net.buses):
            df = df.append({
                    "Number" : bus.number,
                    "Name" : bus.name,
                    "V" : bus.v_mag,
                    "°" : np.rad2deg(bus.v_ang),
                    "V Max" : bus.get_v_max(),
                    "V Min" : bus.get_v_min()
                }, ignore_index=True)

        return df

    def generators(self, net: pfnet.Network):
        """
        Reporte de todas los generadores de una red
        """
        df = pd.DataFrame(columns=['Bus', 'ID', 'P', 'P max', 'P min', 'Q', 'Q max', 'Q min'])
        for gen in reversed(net.generators):
            df = df.append({
                    "Bus" : gen.bus.number,
                    "ID" : gen.name,
                    "P" : gen.P * net.base_power,
                    "P max" : gen.P_max * net.base_power,
                    "P min" : gen.P_min * net.base_power,
                    "Q" : gen.Q * net.base_power,
                    "Q max" : gen.Q_max * net.base_power,
                    "Q min" : gen.Q_min * net.base_power,
                }, ignore_index=True)

        return df

    def branches(self, net: pfnet.Network, parameters=None):
        """
        Reporte de todas las lineas de una red
        """
        keep = []
        if parameters:
            for (_, row) in parameters.monitored.iterrows():
                k, m = int(row['Bus k']), int(row['Bus m'])
                try:
                    ckt = str(int(row['id']))
                except ValueError:
                    ckt = str(row['id'])
                keep.append((k, m, ckt))
            

        df = pd.DataFrame(columns=['Bus k', 'Bus m', 'id', 'Carga %', 'Rating', 'P loss', 'Q loss'])
        for br in reversed(net.branches):

            if br.get_rating('A') > 0:
                carga = max(br.get_S_km_mag(), br.get_S_mk_mag()) / br.get_rating('A') * 100
            else:
                carga = None

            # Skip not monitored branches
            k, m, ckt = br.bus_k.number, br.bus_m.number, br.name.strip()
            if (k, m, ckt) not in keep and parameters:
                continue

            df = df.append({
                    "Bus k" : k,
                    "Bus m" : m,
                    "id" : br.name.strip(),
                    "Carga %" : carga,
                    "Rating" : br.get_rating('A') * net.base_power,
                    "P loss" : (br.get_P_km() + br.get_P_mk()) * net.base_power,
                    "Q loss" : (br.get_Q_km() + br.get_Q_mk()) * net.base_power,
                }, ignore_index=True)
                
        return df
