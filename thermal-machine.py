import socket
import select
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("ip_addr", metavar="<10.1.0.3>", help="Targets IP Address")
parser.add_argument("-p", "--power", dest="power", metavar="", help="on, off, status", default=None, choices=['on', 'off'])
parser.add_argument("-t", "--temp", dest="temp", metavar="", help="set", default=None, choices=['set'])
parser.add_argument("-s", "--status", dest="status", metavar="", help="check", default=None, choices=['check'])
args = parser.parse_args()

if args.temp == "set":
    temp1 = input("Please enter the new Temperature SetPoint: ")

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
        value = temp1
        if len(value) != 4 and len(value) == 3:
            value = value + "0"
        elif len(value) !=4 and len(value) == 2:
            value = "0" + value + "0"
        elif len(value) !=4 and len(value) == 1:
            value = "00" + value + "0"
        Command="MI" + address +"," + str(value)
        self.transact(self.baseCommand)
        print(f"Temperature is set to: {temp1}C")
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
        print(s.WriteMI("0699"))
