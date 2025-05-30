import sys
from PN5180.ISO14443 import ISO14443
from PN5180 import definitions
import time
import signal
import RPi.GPIO as GPIO

def signal_handler(sig, frame):
    print('Recieved SIGINT. Exitting cleanly.')
    GPIO.cleanup()    
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    check_debug = sys.argv[1] if len(sys.argv) == 2 else ''
    debug = True if check_debug == '-v' else False

    reader = ISO14443(debug=False)
    for i in range(0,64):
        print(reader.mifare_authenticate(i))
        print(reader.mifare_block_read(i))
        reader.mifare_halt()
    GPIO.cleanup()
    '''
    while True:
        cards = reader.inventory()
        print(f"{len(cards)} card(s) detected: {' - '.join(cards)}")
        time.sleep(1)
'''