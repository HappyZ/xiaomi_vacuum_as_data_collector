import os
import time
import json
import miio
import codecs
import socket
import binascii
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
    print('help                         - this message')
    print('home                         - move vacuum to dock location')
    print('status                       - print the status of vacuum')
    print('start                        - automatically start one cleaning sesssion and get data')
    print('move auto/pause/stop/home.   - auto scanning movement (no data parsing)')
    print('move rotate speed time       - move (-180, 180)deg at (-0.3,0.3)m/s for `time`ms')
    print('fanspeed integer             - set fan speed to be [1-99]')
    print('goto x_coor y_coor           - move to x,y location on map')
    print('trace on/off                 - manually start/stop collecting trace')
    print('download <trace/map>         - download the trace or map on vacuum, or all if not specified')
    print('config <cmds>                - configuration')
    print('quit/exit                    - exit controller (Ctrl + D does the same)')


def run_ssh_command(cmd):
    try:
        output = subprocess.check_output(
            "ssh -o ConnectTimeout=10 root@${{MIROBO_IP}} '{}'"
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

        self.vacuum = miio.Vacuum(
            ip=self.get_ip(),
            token=self.get_token()
        )

        if forceScan or self.get_ip() is None or self.get_token() is None:
            self.discover()

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

    def _discover(self, timeout=5):
        seen_devices = []
        magic = '21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff'
        # broadcast magic handshake to find devices
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        s.sendto(bytes.fromhex(magic), ('<broadcast>', 54321))
        while 1:
            try:
                data, addr = s.recvfrom(1024)
                m = miio.protocol.Message.parse(data)
                if addr[0] not in seen_devices:
                    seen_device = (
                        addr[0],
                        binascii.hexlify(m.header.value.device_id).decode(),
                        m.checksum
                    )
                    print(
                        "IP {} (ID: {}) - token: {}"
                        .format(
                            seen_device[0],
                            seen_device[1],
                            codecs.encode(seen_device[2], 'hex').decode()
                        )
                    )
                    seen_devices.append(seen_device)
            except socket.timeout:
                print("Discover done!")
                break  # ignore timeouts on discover
            except Exception as e:
                print('Error while reading discover results: {}'.format(e))
                break
        return seen_devices

    def discover(self):
        '''
        getting ip and token of device, e.g., vacuum
        '''
        seen_devices = self._discover()
        if not seen_devices:
            print('Err: cannot find any devices')
            exit(-1)
        if len(seen_devices) == 1:
            self.set_ip(seen_devices[0][0])
            self.vacuum.token = seen_devices[0][2]
            self.set_token(codecs.encode(seen_devices[0][2], 'hex').decode())
            return
        print('Found multiple IPs:')
        for i, seen_device in enumerate(seen_devices):
            print(
                ' {0}. {1} - {2} - {3}'
                .format(i+1, seen_device[0], seen_device[1], seen_device[2])
            )
        try:
            selected = input('Please select one by typing number (1-{}): '.format(len(seen_devices)))
            self.set_ip(seen_devices[int(selected)-1][0])
            self.vacuum.token = seen_devices[int(selected)-1][2]
            self.set_token(codecs.encode(seen_devices[int(selected)-1][2], 'hex').decode())
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
        self.set_token(codecs.encode(m.checksum, 'hex').decode())

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

    def _session_auto(self):
        status = self.vacuum.status()
        if status.battery < 50:
            print("Battery less than 50%, please charge till above 50% to continue")
            return False
        self._control(["trace", "on"])
        self._control(["move", "auto"])
        self._control(["fanspeed", "1"])  # set to lowest fan speed
        while 1:
            try:
                status = self.vacuum.status()
            except KeyboardInterrupt:
                break
            except BaseException as e:
                print("Err: {}".format(e))
                print("Wait for a bit..")
                time.sleep(10)
                continue
            if status.error_code > 0 or status.state_code == 12:
                print("Err: {}".format(status.error))
                try:
                    # try to pause
                    print("Trying to pause due to the error")
                    self.vacuum.pause()
                except BaseException as e:
                    print("Err: cannot pause due to {}".format(e))
                    print("Wait for 30s and restart discovering mode")
                    self.discover()
                    continue
                break
            if status.state_code == 6:
                print("Returning home.. stopping..")
                break
            print(status)
            time.sleep(1)
        self._control(["trace", "off"])
        self._control(["download"])


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
                print("Cleaning old data on device..")
                run_ssh_command(
                    "rm {0}/*.ppm && rm {0}/*.csv".format(self.get_remote_folder())
                )
                print("Enabling trace on the vacuum..")
                if run_ssh_command(
                    "nohup /usr/bin/python3 {0}/get_loc_est.py {0}/{1} > /dev/null 2>&1 &"
                    .format(self.get_remote_folder(), "tmp.csv")
                ) is None:
                    return False
            elif cmd[1] == 'off' or cmd[1] == 'stop' or cmd[1] == 'disable':
                print("Stopping trace collection on vacuum..")
                if run_ssh_command("killall python3") is None:
                    return False
            else:
                print("Unknown command: {}".format(cmd))
                return False
        elif cmd[0] == 'download':
            print("Downloading..")
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
                    "cp /run/shm/*.ppm {0} && ls {0}/*.ppm"
                    .format(self.get_remote_folder())
                )
                if not content:
                    return False
                files = content.rstrip().split('\n')
                if len(files) == 0:
                    print("Cannot find map file!")
                    return False
                print("Found maps: {}".format(files))
                # download only the latest ppm file
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
            elif cmd[1] == 'home':
                print("Returning Home..")
                self.vacuum.home()
            elif len(cmd) > 2:
                try:
                    duration = int(cmd[3]) if len(cmd) > 3 else 1500
                    self.vacuum.manual_control(int(cmd[1]), float(cmd[2]), duration)
                except ValueError:
                    print("Err: rotation in (-180, 180), speed in (-0.3, 0.3), duration as ms in integer (default 1500)")
                    return False
                except BaseException as e:
                    print("Err: {}".format(e))
                    return False
        elif cmd[0] == 'fanspeed':
            if len(cmd) == 1:
                print("Insufficient command")
                return False
            try:
                self.vacuum.set_fan_speed(int(cmd[1]))
            except ValueError:
                print("Err: speed must be integer")
                return False
            except BaseException as e:
                print("Err: {}".format(e))
                return False
        elif cmd[0] == 'goto':
            if len(cmd) < 3:
                print("Insufficient command")
            try:
                self.vacuum.goto(int(cmd[1]), int(cmd[2]))
            except ValueError:
                print("Err: please type into integer")
                return False
        elif cmd[0] == 'start':
            return self._session_auto()
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
    if not c.test_connection():
        c = VacuumController(forceScan=True)
        if not c.test_connection():
            print("Cannot connect to vacuum!")
            exit(-1)

    return c
