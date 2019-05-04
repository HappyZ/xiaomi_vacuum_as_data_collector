from libs.env import get_env_var
from libs.env import set_env_var

from libs.vacuum_controller import VacuumController



def export_ip_token(ip, token):
    print("Exporting to environment variables")
    set_env_var("MIROBO_IP", ip)
    set_env_var("MIROBO_TOKEN", token)

    print("Exporting to `.setup.sh` for later references")
    with open(".setup.sh", "w") as f:
        f.write("export MIROBO_IP={}\n".format(ip))
        f.write("export MIROBO_TOKEN={}\n".format(token))


if __name__ == '__main__':
    ip = get_env_var("MIROBO_IP")
    token = get_env_var("MIROBO_TOKEN")

    c = VacuumController(ip, token)
    if not c.test_connection():
        if ip is None or token is None:
            c = VacuumController()
        assert(c.test_connection())

    export_ip_token(c.ip, c.token)


