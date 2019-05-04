import argparse

from libs.env import get_env_var
from libs.vacuum_controller import init_controller


def help():
    print('Command Menu')
    print('help         - this message')
    print('control      - control the vacuum')
    print('config       - configuration')
    print('update       - upload scripts to vacuum')
    print('quit/exit    - exit controller (Ctrl + D does the same)')


def main(args):
    c = init_controller(args.ip, args.token)
    while 1:
        try:
            cmd = input(">>> ").split(" ")
            if cmd[0] == 'quit' or cmd[0] =='exit':
                print("Exiting..")
                break
            elif cmd[0] == 'help':
                help()
            elif cmd[0] == 'update':
                filepath = cmd[1] if len(cmd) > 1 else "init_vacuum.sh"
                c.update_script(filepath=filepath)
            elif cmd[0] == 'control':
                c.manual_control(cmd[1:])
            elif cmd[0] == 'config':
                c.configuration(cmd[1:])
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            continue
        except EOFError:
            print("Exiting..")
            break
    c.configuration(["save"])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Vacuum Controller'
    )
    parser.add_argument(
        '--ip',
        dest='ip',
        default=get_env_var("MIROBO_IP"),
        help='Specify ip address, default using $MIROBO_IP'
    )
    parser.add_argument(
        '--token',
        dest='token',
        default=get_env_var("MIROBO_TOKEN"),
        help='Specify token str, default using $MIROBO_TOKEN'
    )
    args, __ = parser.parse_known_args()
    main(args)