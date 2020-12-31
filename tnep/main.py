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

        # Botones Optimizar
        self.Optimizar.clicked.connect(self.runTNEP)

        # Botones Output
        self.generarResultados.clicked.connect(self.writeCases)

        # Botones Generar archivos
        self.seleccionarOutput.clicked.connect(self.addExcelReport)
        self.exportarOutput.clicked.connect(self.exportarLastReport) # Sumar funcion

        # Ribbon - File
        self.actionSalir.triggered.connect(self.exit)

        # Ribbon - Flujos TODO: Deberian habilitarse si hay algun caso cargado
        self.actionResolver_NR.triggered.connect(self.runPFNR)
        self.actionResolver_DC.triggered.connect(self.runPFDC)
        self.actionForzar_FS.triggered.connect(self.runPFFS)

        # Ribbon - Reportes TODO: Deberian habilitarse solo si hay algun caso cargado
        self.actionBarras.triggered.connect(lambda: self.reports("buses"))
        self.actionGeneradores.triggered.connect(lambda: self.reports("generators"))
        self.actionLineas.triggered.connect(lambda: self.reports("branches"))

        # Scenarios y memoria para DF
        self.scenarios = {}
        self.lastReport = []

        # Power System Optimization Back End
        self.parser = Parser()
        self.params = Parameters()
        self.report = Reports()
        self.NR = NR()
        self.TNEP = TNEP()


    def enableButtons(self):
        """Desbloquea los botones para correr flujos"""
        if self.listCasos.count() == 0:
            self.generarResultados.setEnabled(False)

            self.actionResolver_NR.setEnabled(False)
            self.actionResolver_DC.setEnabled(False)
            self.actionForzar_FS.setEnabled(False)

            self.actionBarras.setEnabled(False)
            self.actionGeneradores.setEnabled(False)
            self.actionLineas.setEnabled(False)

            self.Optimizar.setEnabled(False)

        else:
            self.generarResultados.setEnabled(True)

            self.actionResolver_NR.setEnabled(True)
            self.actionResolver_DC.setEnabled(True)
            self.actionForzar_FS.setEnabled(True)

            self.actionBarras.setEnabled(True)
            self.actionGeneradores.setEnabled(True)
            self.actionLineas.setEnabled(True)

            if self.params.data != None:
                self.Optimizar.setEnabled(True)
        

    def addRAW(self):
        fileName, _ = QFileDialog.getOpenFileName(self,"Seleccione Escenario", "","PSSE 33 RAW(*.raw);; MATPOWER (*.m)")
        fileName = '/'.join(fileName.split('\\'))

        try:
            if self.scenarios.get(fileName) == None:
                self.scenarios[fileName] = self.parser.parse(fileName)
                self.printOutputBar("Caso Añadido: " + fileName)
                self.listCasos.addItem(fileName)
                self.enableButtons()
            else:
                self.printOutputBar("Caso existente: Se omite la entrada")
        except:
            pass

    def removeRAW(self):
        selectedCases = self.listCasos.selectedItems()
        
        for item in selectedCases:
            net = self.scenarios.pop(item.text())
            self.printOutputBar("Caso Removido: " + item.text())
            self.listCasos.takeItem(self.listCasos.row(item))
        self.enableButtons()


    def addExcel(self):
        fileName, _ = QFileDialog.getOpenFileName(self,"Seleccione Lineas Candidatos", "","Excel (*.xlsx);")
        fileName = '/'.join(fileName.split('\\'))

        try:
            self.params.read_excel(fileName)
            self.printOutputBar("Parametros Añadidos: " + fileName)
            self.excelCandidatos.setText(fileName)
            self.enableButtons()
        except (AssertionError, KeyError):
            self.printOutputBar("Parametros Invalidos: " + fileName)
            self.printOutputBar("Por favor genere la plantilla desde el botón")

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
        rate_percentage = float(self.ratingPercentage.text())
        ens = float(self.ENS.text())
        flow_penalty = float(self.flowPenalty.text())

        _, out_log = self.PSOPT.solveTLEP(rate_percentage, ens, flow_penalty)
        self.printOutputBar(out_log)

    def writeCases(self):
        if self.radioButtonRAW.isChecked():
            _, out_log = self.PSOPT.writeScenarios("raw")   

        if self.radioButtonMATPOWER.isChecked():
            _, out_log = self.PSOPT.writeScenarios("matpower")

        self.printOutputBar(out_log)

    def exit(self):
        close = QtWidgets.QMessageBox.question(self, "Salir",
                                               "¿Desea salir de la aplicación?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if close == QtWidgets.QMessageBox.Yes:
            self.close()

    # TODO:

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = mainProgram()
    MainWindow.show()
    sys.exit(app.exec_())
