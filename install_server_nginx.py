import subprocess
import sys


def run(cmd):
    print(f"\n🚀 {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def check_root():
    uid = subprocess.run("id -u", shell=True, capture_output=True, text=True).stdout.strip()
    if uid != "0":
        print("❌ Please run with sudo or root")
        sys.exit(1)


def update_system():
    run("apt update")
    run("apt upgrade -y")


def install_dependencies():
    run("apt install -y curl ca-certificates gnupg lsb-release ufw software-properties-common")


def install_nginx():
    print("\n====== Installing NGINX ======")

    run("apt install -y nginx")
    run("systemctl enable nginx")
    run("systemctl start nginx")

    run("nginx -v")


def install_docker():
    print("\n====== Installing Docker ======")

    run("apt remove -y docker docker-engine docker.io containerd runc || true")

    run("install -m 0755 -d /etc/apt/keyrings")

    run(
        "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | "
        "gpg --dearmor -o /etc/apt/keyrings/docker.gpg"
    )

    run("chmod a+r /etc/apt/keyrings/docker.gpg")

    run(
        """bash -c 'echo "deb [arch=$(dpkg --print-architecture) \
signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu \
$(lsb_release -cs) stable" \
> /etc/apt/sources.list.d/docker.list'"""
    )

    run("apt update")

    run(
        """apt install -y docker-ce docker-ce-cli containerd.io \
docker-buildx-plugin docker-compose-plugin"""
    )

    run("systemctl enable docker")
    run("systemctl start docker")


def install_fail2ban():
    print("\n====== Installing Fail2Ban ======")

    run("apt install -y fail2ban")

    run("systemctl enable fail2ban")
    run("systemctl start fail2ban")


def configure_fail2ban():
    print("\n====== Configuring Fail2Ban ======")

    jail_config = """
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true
"""

    with open("/etc/fail2ban/jail.local", "w") as f:
        f.write(jail_config)

    run("systemctl restart fail2ban")


def install_certbot():
    print("\n====== Installing Certbot ======")

    run("apt install -y certbot python3-certbot-nginx")


def configure_firewall():
    print("\n====== Configuring Firewall ======")

    run("ufw allow OpenSSH")
    run("ufw allow 'Nginx Full'")
    run("ufw allow 80/tcp")
    run("ufw allow 443/tcp")
    run("ufw --force enable")


def add_user_to_docker():
    print("\n====== Adding user to Docker group ======")

    user = subprocess.run("logname", shell=True, capture_output=True, text=True).stdout.strip()
    run(f"usermod -aG docker {user}")


def verify_installation():
    print("\n====== Verifying installation ======")

    run("nginx -v")
    run("docker --version")
    run("docker compose version")
    run("fail2ban-client status")
    run("certbot --version")


def main():

    check_root()

    print("\n==============================")
    print("SERVER PRODUCTION SETUP")
    print("==============================")

    update_system()
    install_dependencies()

    install_nginx()
    install_docker()

    install_fail2ban()
    configure_fail2ban()

    install_certbot()

    configure_firewall()

    add_user_to_docker()

    verify_installation()

    print("\n==============================")
    print("✅ SERVER READY")
    print("==============================")

    print("\nExample to generate SSL certificate:")
    print("sudo certbot --nginx -d example.com")

    print("\n⚠️ Logout/login to use docker without sudo")


if __name__ == "__main__":
    main()