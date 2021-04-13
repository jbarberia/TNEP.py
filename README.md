# TNEP.py

Este paquete sirve para realizar optimizaciones para la planificacion de la expansion del sistema de transmisión.

![tnep](./tests/data/tnep.png)


# Instalación
La instalación se realiza de la siguiente manera:
```
git clone https://github.com/jbarberia/TNEP.py
cd TNEP.py
pip install -r requirements.txt
python setup.py install
```

NOTA: Es aconsejable utilizar la versión 3.6 del interprete de python, de esta manera se evita cualquier tipo de incopatibilidades con las dependencias.

# Uso

Para utilizar la interfaz grafica se puede correr el script de inicialización que se encuentra en la carpeta `tnep`:

```
python tnep\main.py
```

Tambien este paquete admite un uso dentro de scripts. Dentro de `tests\test_tnep.py` hay varios ejemplos de su utilización.


```python
from tnep import Parser, Parameters, TNEP

# Get cases
parser = Parser()
cases = [data_path + 'Mendoza.raw']
nets = list(map(parser.parse, cases))

# Get parameters
parameters = Parameters()
parameters.read_excel(data_path + 'Mendoza.xlsx')

# Solve model
model = TNEP()
nets_solved, results = model.solve(nets, parameters)
```