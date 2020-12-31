import os
import pfnet as pf

class Parser():
    """
    Object to handle data into PFNET networks
    """

    def __init__(self):
        self.parser_raw = pf.PyParserRAW()
        self.parser_mat = pf.PyParserMAT()

    def select_parser(self, ext):
        """
        returns parser from ext
        """
        if ext.lower() == '.raw':
            return self.parser_raw
        elif ext.lower() == '.m':
            return self.parser_mat
        else:
            raise ValueError('Invalid Extension')

    def parse(self, filename):
        """
        Returns a PFNET network
        """
        name, ext = os.path.splitext(filename)        
        parser = self.select_parser(ext)
        net = parser.parse(filename)

        return net

    def write(self, filename, net):
        """
        Write a .RAW or .m case
        """
        name, ext = os.path.splitext(filename)
        parser = self.select_parser(ext)
        parser.write(net, filename)
