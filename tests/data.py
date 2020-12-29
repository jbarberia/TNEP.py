import os

data_path = os.path.dirname(os.path.realpath(__file__)) + '\\data'

cases = []
parameters = []
for filename in os.listdir(data_path):
    name, ext = os.path.splitext(filename)

    if ext.lower() in ['.raw', '.m']:
        cases.append(data_path + '\\' + filename)

    if ext.lower() in ['.xlsx', '.xls']:
        parameters.append(data_path + '\\' + filename)
