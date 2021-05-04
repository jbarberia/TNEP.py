import os
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from tnep import NR, TNEP, Parser, Parameters, Reports
from tnep import Ui_MainWindow

class mainProgram(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)        
        self.setupUi(self)

        # Botones
        self.agregarCaso.clicked.connect(self.addRAW)
        self.quitarCaso.clicked.connect(self.removeRAW)

        self.agregarCandidatos.clicked.connect(self.addExcel)
        self.Plantilla.clicked.connect(self.createTemplate)

        # Botones Optimizar
        self.Optimizar.clicked.connect(self.runTNEP)
        self.reporteTNEP.clicked.connect(self.TNEPReport)

        # Botones Output
        self.generarResultados.clicked.connect(self.writeCases)

        # Botones Generar archivos
        self.seleccionarOutput.clicked.connect(self.addExcelReport)
        self.exportarOutput.clicked.connect(self.exportarLastReport)

        # Ribbon - File
        self.actionSalir.triggered.connect(self.exit)

        # Ribbon - Flujos
        self.actionResolver_NR.triggered.connect(self.runPFNR)
        self.actionResolver_DC.triggered.connect(self.runPFDC)
        self.actionForzar_FS.triggered.connect(self.runPFFS)

        # Ribbon - Reportes
        self.actionBarras.triggered.connect(lambda: self.reports("buses"))
        self.actionGeneradores.triggered.connect(lambda: self.reports("generators"))
        self.actionLineas.triggered.connect(lambda: self.reports("branches"))

        # Scenarios y memoria para DF
        self.scenarios = {}
        self.solved_nets = {}
        self.tnepReport = None
        self.lastReport = []

        # Power System Optimization Back End
        self.parser = Parser()
        self.params = Parameters()
        self.report = Reports()
        self.NR = NR()
        self.TNEP = TNEP()


    def enableButtons(self):
        """Desbloquea los botones para correr flujos"""
        if not self.tableCasos.rowCount() >= 1:
            self.generarResultados.setEnabled(False)

            self.actionResolver_NR.setEnabled(False)
            self.actionResolver_DC.setEnabled(False)
            self.actionForzar_FS.setEnabled(False)

            self.actionBarras.setEnabled(False)
            self.actionGeneradores.setEnabled(False)
            self.actionLineas.setEnabled(False)

            self.Optimizar.setEnabled(False)
            self.reporteTNEP.setEnabled(False)

        else:
            self.actionResolver_NR.setEnabled(True)
            self.actionResolver_DC.setEnabled(True)
            self.actionForzar_FS.setEnabled(True)

            self.actionBarras.setEnabled(True)
            self.actionGeneradores.setEnabled(True)
            self.actionLineas.setEnabled(True)

            if self.params.candidates is not None and self.params.monitored is not None:
                self.Optimizar.setEnabled(True)

    def addRAW(self):
        fileName, _ = QFileDialog.getOpenFileName(self,"Seleccione Escenario", "","PSSE 33 RAW(*.raw);; MATPOWER (*.m)")
        fileName = '/'.join(fileName.split('\\'))

        try:
            if self.scenarios.get(fileName) == None:
                self.scenarios[fileName] = self.parser.parse(fileName)
                self.printOutputBar("Caso Añadido: " + fileName)
                row_pos = self.tableCasos.rowCount()
                self.tableCasos.insertRow(row_pos)
                item = QtWidgets.QTableWidgetItem(str(fileName))
                item.setFlags(QtCore.Qt.ItemIsEditable)
                self.tableCasos.setItem(row_pos, 0, item)                

                self.enableButtons()
            else:
                self.printOutputBar("Caso existente: Se omite la entrada")
        except:
            pass

    def removeRAW(self):
        index_list = []                                                          
        for row_index in self.tableCasos.selectionModel().selectedRows():       
            index = QtCore.QPersistentModelIndex(row_index)         
            index_list.append(index)   
        for index in index_list:                                      
            filename = index.data()
            self.scenarios.pop(filename)
            self.tableCasos.removeRow(index.row())
            self.printOutputBar("Caso Removido: " + filename)
        self.enableButtons()         


    def addExcel(self):
        fileName, _ = QFileDialog.getOpenFileName(self,"Seleccione Lineas Candidatos", "","Excel (*.xlsx);")
        fileName = '/'.join(fileName.split('\\'))
        try:
            self.params.read_excel(fileName)
            self.printOutputBar("Parametros Añadidos: " + fileName)
            self.excelCandidatos.setText(fileName)
            self.Optimizar.setEnabled(True)
            self.enableButtons()
        except (ValueError, AssertionError, KeyError):
            self.printOutputBar("Parametros Invalidos: " + fileName)
            self.printOutputBar("Por favor genere la plantilla desde el botón")


    def createTemplate(self):
        folder = str(QFileDialog.getExistingDirectory(None, "Select Directory"))
        filename = folder + '\\plantilla.xlsx'
        self.params.generate_template(filename)
        self.printOutputBar("Plantilla generada en: {}".format(filename))
    

    def addExcelReport(self):
        fileName, _ = QFileDialog.getOpenFileName(self,"Seleccione Lineas Candidatos", "","Excel (*.xlsx);")
        fileName = '/'.join(fileName.split('\\'))

        if fileName != "":
            self.excelOutput.setText(fileName)
            self.pathOutput = fileName
            self.printOutputBar("Los reportes generados se escribiran en: " + fileName)
            self.printOutputBar("Recuerde que se escribira el ultimo reporte generado en la Output Bar")

            self.exportarOutput.setEnabled(True)


    def exportarLastReport(self):
        if len(self.lastReport) > 0:
            for df, scenario in zip(self.lastReport, self.scenarios.keys()):
                fileName = self.pathOutput
                sheet = self.outputHoja.text() + '' + scenario.split('/')[-1]
                self.report.to_excel(df, fileName, sheet)
                self.printOutputBar("Reporte escrito en la hoja: {}".format(sheet))
            if len(self.lastReport) > len(self.scenarios.keys()):
                sheet = self.outputHoja.text() + 'Recorte de demanda'
                self.report.to_excel(self.lastReport[-1], fileName, sheet)
                self.printOutputBar("Reporte escrito en la hoja: {}".format(sheet))
        else:
            self.printOutputBar("Todavia no se corrio ningun reporte")
        

    def printOutputBar(self, log):
        self.textOutputBar.append(log)


    def runPFNR(self):
        for fileName, net in self.scenarios.items():
            self.NR.solve_ac(net)
            self.printOutputBar(fileName + ":")
            self.printOutputBar("P mis. : {:.4f} MW".format(net.bus_P_mis*net.base_power))
            self.printOutputBar("P mis. : {:.4f} MVAr".format(net.bus_Q_mis*net.base_power))


    def runPFDC(self):
        for fileName, net in self.scenarios.items():
            self.NR.solve_dc(net)
            self.printOutputBar(fileName + ":")
            self.printOutputBar("P mis. : {:.4f} MW".format(net.bus_P_mis*net.base_power))
            self.printOutputBar("P mis. : {:.4f} MVAr".format(net.bus_Q_mis*net.base_power))


    def runPFFS(self):
        for net in self.scenarios.values():
            for bus in net.buses:
                if not bus.is_v_set_regulated():
                    bus.v_mag = 1.0
                bus.v_ang = 0.0
        self.printOutputBar("Tensiones seteadas en 1.0 /_ 0.0°")


    def reports(self, component):
        self.lastReport = []
        for net in self.scenarios.values():
            if component == "buses":
                df = self.report.buses(net)
            if component == "generators":
                df = self.report.generators(net)
            if component == "branches":
                df = self.report.branches(net)
            
            self.lastReport.append(df)
            self.printOutputBar(df.to_string())


    def runTNEP(self):
        rows = self.tableCasos.rowCount()
        self.TNEP.D_k = [float(self.tableCasos.item(i, 1).text()) for i in range(rows)]
        self.TNEP.T_k = [float(self.tableCasos.item(i, 2).text()) for i in range(rows)]
        self.TNEP.F_k = [float(self.tableCasos.item(i, 3).text()) for i in range(rows)]

        self.TNEP.r = float(self.tasaDescuento.text())
        self.TNEP.n = float(self.anios.text())

        self.TNEP.options['rate factor'] = float(self.ratingPercentage.text())
        self.TNEP.options['penalty'] = float(self.flowPenalty.text())
        self.TNEP.options['ens'] = float(self.ENS.text())
        
        # PreProceso
        pre_dfs = []
        for net in self.scenarios.values():
            self.NR.solve_ac(net)
            df = self.report.branches(net, self.params)
            pre_dfs.append(df)
        
        solved_nets, resultado = self.TNEP.solve(
            self.scenarios.values(),
            self.params
        )
        self.printOutputBar('----------------------------------------------------------')
        self.printOutputBar('Optimizacion con resultado: {}'.format(resultado['status']))
        self.printOutputBar('Se construyeron: {} Lineas'.format(resultado['br_builded']))
        self.printOutputBar('Costo de lineas: {}'.format(resultado['br_cost']))
        self.printOutputBar('Penalidad sobrecarga: {}'.format(resultado['overload']))
        self.printOutputBar('ENS: {}'.format(resultado['ens']))
        self.printOutputBar('Funcion Objetivo: {}'.format(resultado['objective']))
        
        # Escribir las redes en objeto
        for fileName, net in zip(self.scenarios.keys(), solved_nets):
            name, ext = os.path.splitext(fileName)
            self.solved_nets[name+'-Resuelto'+ext] = net

        # PostProceso
        pos_dfs = []
        for net in solved_nets:
            self.NR.solve_ac(net)
            df = self.report.branches(net, self.params)
            pos_dfs.append(df)
        
        dfs = []
        for pre_df, pos_df in zip(pre_dfs, pos_dfs):
            # Rename
            pre_df = pre_df.rename(columns={'Carga %': 'Pre. Opt. Carga %'})
            pos_df = pos_df.rename(columns={'Carga %': 'Pos. Opt. Carga %'})

            # Slice df
            pre_df = pre_df.loc[:, ['Bus k', 'Bus m', 'id', 'Pre. Opt. Carga %']]
            pos_df = pos_df.loc[:, ['Bus k', 'Bus m', 'id', 'Pos. Opt. Carga %']]

            # Join
            df = pd.merge(pre_df, pos_df, how='outer', on=["Bus k", "Bus m", "id"])

            # Add to list
            dfs.append(df)

        # Add df of load shed
        dfs.append(self.report.load_shed(
            list(self.scenarios.values()),
            list(self.solved_nets.values()),
            self.params
        ))

        self.tnepReport = dfs
        self.reporteTNEP.setEnabled(True)
        self.generarResultados.setEnabled(True)


    def TNEPReport(self):
        for df, filename in zip(self.tnepReport, self.solved_nets):
            self.printOutputBar(filename + ":")
            self.printOutputBar(df.to_string())
        # El ultimo df son los recortes de carga
        self.printOutputBar(self.tnepReport[-1].to_string())
        self.lastReport = self.tnepReport
        

    def writeCases(self):
        for filename, net in self.solved_nets.items():
            name, ext = os.path.splitext(filename)
            if self.radioButtonRAW.isChecked():
                filename = name + '.raw'
            if self.radioButtonMATPOWER.isChecked():
                filename = name + '.m'
            self.parser.write(filename, net)
            self.printOutputBar("Caso generado en: " + filename)


    def exit(self):
        close = QtWidgets.QMessageBox.question(self, "Salir",
                                               "¿Desea salir de la aplicación?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if close == QtWidgets.QMessageBox.Yes:
            self.close()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = mainProgram()
    MainWindow.show()
    sys.exit(app.exec_())
