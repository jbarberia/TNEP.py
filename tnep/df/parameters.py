import os
import pandas as pd


class Parameters():
    """
    Clase para manipular archivos de Excel
    con la parametrizacion del TNEP
    """

    def __init__(self):
        self.data = None

    def read_excel(self, filename, sheet='Parametros'):
        """
        Lee un archivo de excel con los parametros
        """
        # Read Excel
        filename = self.check_name(filename)
        df = pd.read_excel(filename, sheet_name=sheet)

        # Check Columns
        default_col = ['Bus k', 'Bus m', 'r', 'x', 'b', 'Rating', 'Costo']
        assert set(default_col) <= set(df.columns)

        self.data = df
        return self.data


    def generate_template(self, filename):
        """
        Genera una plantilla para cargar los datos
        """
        filename = self.check_name(filename)

        # empty template
        columns = ['Bus k', 'Bus m', 'r', 'x', 'b', 'Rating', 'Costo']
        df = pd.DataFrame(columns=columns)

        # to excel
        writer = pd.ExcelWriter(filename)
        df.to_excel(writer, 'Parametros')
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