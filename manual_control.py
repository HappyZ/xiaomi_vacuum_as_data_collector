import miio
import codecs
import socket


def discover_devices():
    timeout = 5
    seen_addrs = []  # type: List[str]
    addr = '<broadcast>'
    # magic, length 32
    helobytes = bytes.fromhex('21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff')
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(timeout)
    s.sendto(helobytes, (addr, 54321))
    while True:
        try:
            data, addr = s.recvfrom(1024)
            if addr[0] not in seen_addrs:
                seen_addrs.append(addr[0])
        except socket.timeout:
            break  # ignore timeouts on discover
        except Exception as ex:
            print('Error while reading discover results:', ex)
            break
    return seen_addrs


def select_item(welcome_text, items):
    print(welcome_text)
    for i, item in enumerate(items):
        print('{}. {}'.format(i+1, item))
    try:
        selected = input('Please select option by typing number (1-{}): '.format(len(items)))
        result = items[int(selected)-1]
        return result
    except KeyboardInterrupt:
        print('User requested to exit')
        exit()
    except ValueError:
        print('Error! Please enter only one number')
        exit()
    except IndexError:
        print('Error! Please enter one number between 1-{}'.format(len(items)))
        exit()


ip_address = None
known_token = None

if not ip_address:
    print('Address is not set. Trying to discover.')
    seen_addrs = discover_devices()

    if len(seen_addrs) == 0:
        print('No devices discovered.')
        exit()
    elif len(seen_addrs) == 1:
        ip_address = seen_addrs[0]
    else:
        ip_address = select_item('Choose device for connection:', seen_addrs)

vacuum = miio.Vacuum(ip=ip_address, token=known_token)

if not known_token:
    print('Sending handshake to get token')
    m = vacuum.do_discover()
    vacuum.token = m.checksum
    known_token = codecs.encode(m.checksum, 'hex')
else:
    if len(known_token) == 16:
        known_token = str(binascii.hexlify(bytes(known_token, encoding="utf8")))

print("ip_address: {}".format(ip_address))
print("known_token: {}".format(known_token))

try:
    s = vacuum.status()
    print(s)
except Exception as ex:
    print('error while checking device:', ex)
    exit()

vacuum.home()
