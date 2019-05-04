import os
import time
import json
import miio
import codecs
import socket
import subprocess

from libs.env import set_env_var


def config_help():
    print('Config Command Menu')
    print('help             - this message')
    print('set <key> <val>  - set key value in config')
    print('get <key>        - get config from key, if `key` not set, print all')
    print('save/load <file> - save/load configuration from file (default: ./config.json)')
    print('quit/exit        - exit controller (Ctrl + D does the same)')


def control_help():
    print('Control Command Menu')
    print('help                     - this message')
    print('home                     - move vacuum to dock location')
    print('move auto/pause/stop.    - auto scanning movement (no data parsing)')
    print('move rotate speed time   - move (-180, 180)deg at (-0.3,0.3)m/s for `time`ms')
    print('goto x_coor y_coor       - move to x,y location on map')
    print('trace on/off             - manually start/stop collecting trace')
    print('download trace/map       - download the trace or map on vacuum')
    print('config <cmds>            - configuration')
    print('quit/exit                - exit controller (Ctrl + D does the same)')


def run_ssh_command(cmd):
    try:
        output = subprocess.check_output(
            "ssh -o ConnectTimeout=10 -t root@${{MIROBO_IP}} '{}'"
            .format(cmd),
            shell=True
        ).decode()
    except BaseException as e:
        print("Err: {}".format(e))
        return None
    return output


def fetch_file_from_vacuum(remote_fp, local_fp="./"):
    try:
        subprocess.check_output(
            "scp -o ConnectTimeout=10 root@${{MIROBO_IP}}:{} {}"
            .format(remote_fp, local_fp),
            shell=True
        )
        return True
    except BaseException as e:
        print("Err: {}".format(e))
    return False


def export_ip_token(ip, token):
    print("Exporting to environment variables")
    set_env_var("MIROBO_IP", ip)
    set_env_var("MIROBO_TOKEN", token)


class VacuumController():
    '''
    controlling xiaomi vacuum
    '''

    def __init__(self, ip=None, token=None, forceScan=False):
        self.config = {}
        self.tmp = {}

        # load old config if exist
        self.configuration(["load"])
        if forceScan:
            print("Ignore prior IP and token, force to scan again!")

        # if forcely specify a new ip and/or token
        if ip:
            self.set_ip(ip)
        if token:
            self.set_token(token)

        # if we still don't have an IP address, or asked to scan anyways
        if forceScan or self.get_ip() is None:
            self.finding_ip()

        self.vacuum = miio.Vacuum(
            ip=self.get_ip(),
            token=self.get_token()
        )

        # now if we still don't have a valid token, or asked to scan anyways
        if forceScan or self.get_token() is None:
            self.fetching_token()

        export_ip_token(self.get_ip(), self.get_token())

    def get_ip(self):
        return self.config.get("ip", None)

    def set_ip(self, ip):
        self.set_config("ip", ip)

    def get_token(self):
        return self.config.get("token", None)

    def set_token(self, token):
        self.set_config("token", token)

    def get_remote_folder(self):
        return self.config.get("remote_script_folder", "/mnt/data/exp")

    def set_config(self, key, val):
        self.config[key] = val

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
            self.set_ip(ips[0])
            return
        print('Found multiple IPs:')
        for i, ip in enumerate(ips):
            print(' {0}. {1}'.format(i+1, ip))
        try:
            selected = input('Please select one by typing number (1-{}): '.format(len(ips)))
            self.set_ip(ips[int(selected)-1])
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

    def fetching_token(self):
        '''
        getting token by handshaking with vacuum
        '''
        print('Sending handshake to get token')
        m = self.vacuum.do_discover()
        self.vacuum.token = m.checksum
        self.set_token(codecs.encode(m.checksum, 'hex'))

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

    def update_script(self, filepath="init_vacuum.sh"):
        subprocess.call("./{}".format(filepath, ), shell=True)
        return

    def _config(self, cmd):
        if cmd[0] == 'help':
            config_help()
        elif cmd[0] == 'quit' or cmd[0] =='exit':
            raise EOFError
        elif cmd[0] == 'set':
            if len(cmd) < 3:
                print("Insufficient command")
                return
            self.set_config(cmd[1], cmd[2])
        elif cmd[0] == 'get':
            if len(cmd) == 1:
                print(self.config)
            else:
                [print(self.config.get(val, None)) for val in cmd[1:]]
        elif cmd[0] == 'save':
            filepath = cmd[1] if len(cmd) > 1 else './config.json'
            json.dump(self.config, open(filepath, 'w'))
            print("Configs: {}".format(self.config))
            print("Saved to {}".format(filepath))
        elif cmd[0] == 'load':
            filepath = cmd[1] if len(cmd) > 1 else './config.json'
            if not os.path.isfile(filepath):
                print("{} does not exit".format(filepath))
                return
            self.config = json.load(open(filepath, 'r'))
            print("Loaded from {}".format(filepath))
            print("Configs: {}".format(self.config))

    def configuration(self, cmd=None):
        '''
        configuration
        '''
        if cmd:
            self._config(cmd)
            return
        while 1:
            try:
                cmd = input("config >>> ").split(" ")
                self._config(cmd)
            except KeyboardInterrupt:
                print("KeyboardInterrupt")
                continue
            except EOFError:
                print("Exiting config..")
                break
            except BaseException as e:
                print("Err: {}".format(e))
                raise

    def _control(self, cmd):
        if cmd[0] == 'help':
            control_help()
        elif cmd[0] == 'quit' or cmd[0] =='exit':
            raise EOFError
        elif cmd[0] == 'config':
            self.configuration(cmd[1:])
        elif cmd[0] == 'trace':
            if len(cmd) == 1:
                print("Insufficient command")
                return False
            if cmd[1] == 'on' or cmd[1] == 'start' or cmd[1] == 'enable':
                print("Running script on vacuum..")
                if run_ssh_command(
                    "python3 {0}/get_loc_est.py {1} &"
                    .format(self.get_remote_folder, "tmp.csv")
                ) is None:
                    return False
            elif cmd[1] == 'off' or cmd[1] == 'stop' or cmd[1] == 'disable':
                print("Stopping python3..")
                if run_ssh_command("killall python3") is None:
                    return False
            else:
                print("Unknown command: {}".format(cmd))
                return False
        elif cmd[0] == 'download':
            prefix = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            if len(cmd) == 1:
                return (
                    self._control(['download', 'map', prefix]) and
                    self._control(['download', 'trace', prefix])
                )
            if cmd[1] == 'trace':
                # download the file, after then we delete it 
                if not fetch_file_from_vacuum(
                    "{}/tmp_slam.csv"
                    .format(self.get_remote_folder()),
                    "./{}_loc.csv"
                    .format(cmd[2] if len(cmd) > 2 else prefix)
                ):
                    return False
            elif cmd[1] == 'map':
                # find file first
                content = run_ssh_command(
                    "ls /run/shm/*.ppm"
                )
                if not content:
                    return False
                files = content.rstrip().split('\n')
                if len(files) == 0:
                    print("Cannot find map file!")
                    return False
                # download only the last ppm file
                if not fetch_file_from_vacuum(
                    files[-1],
                    "./{}_map.ppm".format(cmd[2] if len(cmd) > 2 else prefix)
                ):
                    return False
            else:
                print("Unknown command: {}".format(cmd))
                return False
        elif cmd[0] == 'home':
            print("Returning Home..")
            self.vacuum.home()
        elif cmd[0] == 'status':
            print(self.vacuum.status())
        elif cmd[0] == 'move':
            if len(cmd) == 1:
                print("Insufficient command")
                return False
            if cmd[1] == 'auto':
                print("Starting..")
                self.vacuum.start()
            elif cmd[1] == 'pause':
                print("Pausing..")
                self.vacuum.pause()
            elif cmd[1] == 'stop':
                print("Stopping..")
                self.vacuum.stop()
            elif len(cmd) > 2:
                try:
                    duration = int(cmd[3]) if len(cmd) > 3 else 1500
                    self.vacuum.manual_control(int(cmd[1]), float(cmd[2]), duration)
                except ValueError:
                    print("Err: rotation in (-180, 180), speed in (-0.3, 0.3), duration as ms in integer (default 1500)")
                return False
        elif cmd[0] == 'goto':
            if len(cmd) < 3:
                print("Insufficient command")
            try:
                self.vacuum.goto(int(cmd[1]), int(cmd[2]))
            except ValueError:
                print("Err: please type into integer")
                return False
        return True


    def manual_control(self, cmd=None):
        '''
        manual control
        '''
        if cmd:
            self._control(cmd)
            return
        while 1:
            try:
                cmd = input("control >>> ").split(" ")
                self._control(cmd)
            except KeyboardInterrupt:
                print("KeyboardInterrupt")
                continue
            except EOFError:
                print("Exiting control..")
                break
            except BaseException as e:
                print("Err: {}".format(e))
                raise


def init_controller(ip, token):
    c = VacuumController(ip=ip, token=token, forceScan=False)
    # if not c.test_connection():
    #     c = VacuumController(forceScan=True)
    #     if not c.test_connection():
    #         print("Cannot connect to vacuum!")
    #         exit(-1)

    return c