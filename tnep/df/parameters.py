import os
import pandas as pd


class Parameters():
    """
    Clase para manipular archivos de Excel
    con la parametrizacion del TNEP
    """

    def __init__(self):
        self.candidates = None
        self.monitored = None
        self.loads = None

    def read_excel(self, filename, sheet='Parametros'):
        """
        Lee un archivo de excel con los parametros
        """       
        # Read Excel
        filename = self.check_name(filename)
        df_candidates = pd.read_excel(filename, sheet_name='Candidatas')
        df_monitored = pd.read_excel(filename, sheet_name='Monitoreadas')
        df_loads = pd.read_excel(filename, sheet_name='Recorte Carga')

        # Check Columns
        default_col_can = ['Bus k', 'Bus m', 'id', 'r', 'x', 'b', 'Rating', 'Costo']
        default_col_mon = ['Bus k', 'Bus m', 'id', 'Rating']
        default_col_load = ['Bus', 'Recorte Max']
        assert set(default_col_can) <= set(df_candidates.columns)
        assert set(default_col_mon) <= set(df_monitored.columns)
        assert set(default_col_load) <= set(df_loads.columns)

        self.candidates = df_candidates
        self.monitored = df_monitored
        self.loads = df_loads


    def generate_template(self, filename):
        """
        Genera una plantilla para cargar los datos
        """
        filename = self.check_name(filename)

        # empty template - candidates
        columns_can = ['Bus k', 'Bus m', 'id', 'r', 'x', 'b', 'Rating', 'Costo']
        columns_mon = ['Bus k', 'Bus m', 'id', 'Rating']
        columns_load = ['Bus', 'Recorte Max']
        df_can = pd.DataFrame(columns=columns_can)
        df_mon = pd.DataFrame(columns=columns_mon)
        df_loads = pd.DataFrame(columns=columns_load)

        # to excel
        writer = pd.ExcelWriter(filename)
        df_can.to_excel(writer, 'Candidatas')
        df_mon.to_excel(writer, 'Monitoreadas')
        df_loads.to_excel(writer, 'Recorte Carga')
        writer.save()

    def check_name(self, filename):
        """
        Verifica que la extension sea .xlsx
        """
        name, ext = os.path.splitext(filename)
        if ext.lower() in ['.xlsx', '.xls']:
            return filename
        else:
            raise ValueError('Invalid Excel extension')
