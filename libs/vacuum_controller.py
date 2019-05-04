import miio
import codecs
import socket


class VacuumController():
    '''
    controlling xiaomi vacuum
    '''

    def __init__(self, ip=None, token=None):
        self.ip = ip
        self.token = token

        if self.ip is None:
            self.finding_ip()

        self.vacuum = miio.Vacuum(ip=self.ip, token=self.token)

        if self.token is None:
            self.get_token()

    def _discover_devices(self, timeout=5):
        ips = []
        # broadcast magic handshake to find devices
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        s.sendto(
            bytes.fromhex('21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff'),
            ('<broadcast>', 54321)
        )
        while 1:
            try:
                __, addr = s.recvfrom(1024)
                if addr[0] not in ips:
                    ips.append(addr[0])
            except socket.timeout:
                break  # ignore timeouts on discover
            except Exception as e:
                print('Error while reading discover results: {}'.format(e))
                break
        return ips

    def finding_ip(self):
        '''
        getting ip of vacuum
        '''
        ips = self._discover_devices()
        if not ips:
            print('Err: cannot find any vacuum IP')
            exit(-1)
        if len(ips) == 1:
            self.ip = ips[0]
            return
        print('Found multiple IPs:')
        for i, ip in enumerate(ips):
            print(' {0}. {1}'.format(i+1, ip))
        try:
            selected = input('Please select one by typing number (1-{}): '.format(len(ips)))
            self.ip = ips[int(selected)-1]
        except KeyboardInterrupt:
            print('User requested to exit')
            exit(0)
        except ValueError:
            print('Err: Please enter only one number')
            exit(-1)
        except IndexError:
            print('Err: Please enter one number between 1-{}'.format(len(ips)))
            exit(-1)
        except BaseException as e:
            print('Err: {}'.format(e))
            exit(-1)

    def get_token(self):
        '''
        getting token by handshaking with vacuum
        '''
        print('Sending handshake to get token')
        m = self.vacuum.do_discover()
        self.vacuum.token = m.checksum
        self.token = codecs.encode(m.checksum, 'hex')

    def test_connection(self):
        '''
        test connection
        '''
        try:
            s = self.vacuum.status()
            print(s)
            return True
        except Exception as e:
            print('Err: {}'.format(e))
        return False
