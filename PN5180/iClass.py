import time
from PN5180 import AbstractPN5180
from PN5180.definitions import *

class iClass(AbstractPN5180):
    def __init__(self, bus: int = 0, device: int = 0, debug=False):
        super().__init__(bus, device, debug)
        self.load_rf_config(0x0d, 0x8d) #ISO15693
        self.rf_on()
        print(self.get_irq_status())
    
    def issue_iclass_command(self, cmd: list):
        self.send_data(cmd, len(cmd))
        time.sleep(0.01)

        if (self.get_irq_status() & RX_SOF_DET_IRQ_STAT) == 0:
            print("EC NO CARD")
        
        rx_status = self.read_register(RX_STATUS)
        rx_status_len = rx_status & 0x000001ff

        result_ptr = self.read_data(rx_status_len)
        print(result_ptr)
        '''TODO: Error handle here'''

        irq_status = self.get_irq_status()
        if 0 == (RX_SOF_DET_IRQ_STAT & irq_status):
            self.clear_IRQ_STATUS()
            print("EC NO CARD")
        
        if RX_SOF_DET_IRQ_STAT == (RX_SOF_DET_IRQ_STAT & irq_status):
            self.clear_IRQ_STATUS()
            print("ICLASS EC OK")

    def activate_all(self):
        self._write_register(CRC_RX_CONFIG, [0x00,0x00,0x00,0x00])
        self._write_register(CRC_TX_CONFIG, [0x00,0x00,0x00,0x00])

        self.issue_iclass_command([ICLASS_CMD_ACTALL])