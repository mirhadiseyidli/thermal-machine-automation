import socket, select, argparse, pexpect, serial, sys
from pexpect import fdpexpect
from time import sleep

parser = argparse.ArgumentParser()
parser.add_argument("ip_addr", metavar="<10.1.0.3>", help="Targets IP Address")
parser.add_argument("usbCon", metavar="</dev/ttyUSB*>", help="USB Connection (full path)")
parser.add_argument("-p", "--power", dest="power", metavar="", help="on, off, status", default=None, choices=['on', 'off'])
parser.add_argument("-t", "--temp", dest="temp", metavar="", help="set", default=None, choices=['set'])
parser.add_argument("-s", "--status", dest="status", metavar="", help="check", default=None, choices=['check'])
parser.add_argument("-d", "--device", dest="device", metavar="", help="horta, dune", default=None, choices=['horta', 'dune', 'dune-socket', 'horta-socket'])
args = parser.parse_args()
usbCon = args.usbCon
device = args.device

fd = serial.Serial(usbCon, 115200, timeout=1) #Connect to the Serial port
ss = fdpexpect.fdspawn(fd, encoding='utf-8') #Opens the serial port as a child process
ss.delaybeforesend = 5 #Delays sending commands

def templimit():
    global limitlow
    global limithigh
    if device.lower() == 'dune' or device.lower() == 'dune-socket':
        if device.lower() == 'dune-socket':
            limitlow = -30
            limithigh = 95
        else:
            limitlow = -50
            limithigh = 125
    elif device.lower() == 'horta' or device.lower() == 'horta-socket':
        if device.lower() == 'horta-socket':
            limitlow = -50
            limithigh = 125
        else:
            limitlow = -30
            limithigh = 95
    
class MDSocket:
    def __init__(self,ip_addr,tcp_port,timeout_secs):
        self.s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.ip=ip_addr
        self.tcp=tcp_port
        self.to=timeout_secs
        self.baseCommand="m"
        self.rxbufsize = 1024
        self.read_all_at_once = True
        
    #connect
    def connect(self):
        self.s.setblocking(0)
        self.s.settimeout(self.to)
        self.s.connect((self.ip,self.tcp))
    #disconnect
    def disconnect(self):
        if self.s!=None:
            self.s.close()

    #send command string to connected socket
    def send(self, command):
        if self.s is None:
            raise OSError('Socket error; not connected')
        
        buf = bytes(command, 'ascii')
        try:
            self.s.sendall(buf)
        except OSError as e:
            raise OSError("Socket error; send failure (sending \'%s\')" % command.strip())
    #receive response from connected socket
    def receive(self):
        if self.s is None:
            raise OSError('Socket error; not connected')

        bytes = bytearray()
        while True:
            try:
                readable, writeable, error = select.select([self.s], [], [], self.to)
            except Exception as e:
                raise OSError("Socket error; read failure")

            if readable:
                data = self.s.recv(self.rxbufsize)
                if not data:
                    raise OSError('Socket error; no data on readable socket')
                else:
                    bytes += data
                    if self.read_all_at_once:
                        break
            else:
                break

        response = str(bytes, 'utf-8', errors="ignore").rstrip('\r\n')
        return response

    def transact(self, command):
        self.send(command)
        response = self.receive()
        return response
    #Read MI Registar from machine       
    def ReadMI(self,address):
        if self.s is None:
            raise OSError('Socket error;not connected')
        Command="MI" + address +"?"
        self.transact(self.baseCommand)
        print ('Checking the SetPoint temperature:')
        string = self.transact(Command)
        string = string.replace('MI699,', "")
        string = int(string) // 10
        return f"Temperature: {string}C"
    
    def ReadMII(self,address):
        if self.s is None:
            raise OSError('Socket error;not connected')
        Command="MI" + address +"?"
        self.transact(self.baseCommand)
        print ('Checking the Actual temperature:')
        string = self.transact(Command)
        string = string.replace('MI6,', "")
        string = int(string) // 10
        return f"Temperature: {string}C"

    #Read MB Registar from machine    
    def ReadMB(self,address):
        if self.s is None:
            raise OSError('Socket error;not connected')
        Command="MB" + address +"?"
        self.transact(self.baseCommand)
        print ('Checking the power status: ')
        if "MB20,0" in self.transact(Command):
            return "Power is on"
        elif "MB20,1" in self.transact(Command):
            return "Power is off"
        
    #Write MI Registar with specified value
    def WriteMI(self,address):
        if self.s is None:
            raise OSError('Socket error;not connected')
        value = str(temp2)
        if len(value) != 4 and len(value) == 3:
            value = value + "0"
        elif len(value) !=4 and len(value) == 2:
            value = "0" + value + "0"
        elif len(value) !=4 and len(value) == 1:
            value = "00" + value + "0"
        Command="MI" + address +"," + str(value)
        self.transact(self.baseCommand)
        print(f"Temperature is set to: {temp2}C")
        return self.transact(Command)
    
    def WriteMII(self,address):
        if self.s is None:
            raise OSError('Socket error;not connected')
        if int(temp1) >= 85:
            value = str(limithigh)
            print(f"Temperature is set to: {value}C")
        elif int(temp1) <= 0:
            value = str(limitlow)
            print(f"Temperature is set to: {value}C")
        else:
            value = str(temp2)
        if len(value) != 4 and len(value) == 3:
            value = value + "0"
        elif len(value) !=4 and len(value) == 2:
            value = "0" + value + "0"
        elif len(value) !=4 and len(value) == 1:
            value = "00" + value + "0"
        Command="MI" + address +"," + str(value)
        self.transact(self.baseCommand)
        return self.transact(Command)
        
    #Write MB Registar with specified value    
    def WriteMB(self,address, value):
        if self.s is None:
            raise OSError('Socket error;not connected')
        Command="MB" + address +"," + str(value)
        self.transact(self.baseCommand)
        return self.transact(Command)

#main
if __name__ =='__main__':
    #socket info
    ip_addr=args.ip_addr
    tcp_port=5000
    timeout_secs = 3
    s=MDSocket(ip_addr,tcp_port,timeout_secs)
    print('Connecting...')
    s.connect()
    if args.status == "check":
        print(s.ReadMB("0020"))
        print(s.ReadMI("0699"))
        print(s.ReadMII("0006"))
    if args.power == "on":
        print(s.WriteMB("0020",0))
        print("Power turned on")
    elif args.power == "off":
        print(s.WriteMB("0020",1))
        print("Power turned off")
    if args.temp == "set":
        temp1 = input("Please enter the Junction Temperature SetPoint: ")
        temp2 = temp1
        templimit()
        print(s.WriteMII("0699"))
        ss.sendline('cd /root/')
        ss.expect('#', timeout=None)
        if "dune" in device.lower():
            ss.sendline('./set_tsense.sh') #Make sure filename matches the one on your system
            ss.expect('#', timeout=None)
        i = 0
        try:
            while i < 100:
                ss.sendline('./tsense.sh') #Make sure filename matches the one on your system
                ss.expect('#', timeout=None)
                string = str(ss.before)
                if "panic" in string or "kernel" in string or "Dune" in string or "end" in string or "trace" in string or "CPU" in string:
                    print("\n--- Kernel Panic ---\n")
                    sys.exit(0)
                elif "random: crng init done" not in string:
                    if 'dune' in device.lower():
                        string = string.replace("./tsense.sh", "")
                        string = string.replace("Temperature is ", "")
                        string = string.replace("C", "")
                        string = string.replace("\r\n", "")
                        string = string.replace(" \x1b[6n", "")
                        print(f"Junction Temperature is {string}C")
                    elif 'horta' in device.lower():
                        string = string.replace("./max_tsens.sh", "")
                        string = string.replace("max temp: ", "")
                        string = string.replace("C", "")
                        print(f"Junction Temperature is {string}C")
                    if int(string) <= (int(temp1) - 3) and int(string) >= (int(temp1) - 10) and int(temp2) < limithigh:
                        temp2 = int(temp2) + 1
                        if i > 0:
                            i -= 1
                        print(s.WriteMI("0699"))
                    elif int(string) >= (int(temp1) + 3) and int(string) <= (int(temp1) + 10) and int(temp2) > limitlow:
                        temp2 = int(temp2) - 1
                        if i > 0:
                            i -= 1
                        print(s.WriteMI("0699"))
                    elif int(string) == int(temp1) or int(string) == int(temp1) + 2 or int(string) == int(temp1) - 2:
                        i += 1
                sleep(1)
            print("\nTemperature is stable, exiting the software...")
            ss.close()
            sys.exit(0)
        except KeyboardInterrupt:
            print("\nInterrupted manually.\nClosing...")
            sys.exit(0)
