import os
import subprocess
import getpass

# === PROMPTS UTILISATEUR ===
project_name = input("🔧 Project name : ").strip()
domain = input("🌐 DOMAINE NAME OR IP ADDR (ex: monsite.com) : ").strip()
git_repo = input("📦  Git REPOT(HTTPS ou SSH) : ").strip()
mysql_db = input("🛢️  DATABASE NAME : ").strip()
mysql_user = "appuser"
mysql_password = getpass.getpass("🔑 Mysql APP password (invisible) : ")
mysql_root_password = getpass.getpass("🔐 Mysql ROOT PASSWORD(invisible) : ")

project_dir = f"/var/www/{project_name}"
deploy_user = "deploy"

# === Commande Helper ===
def run(cmd):
    print(f"\n🚀 {cmd}")
    subprocess.run(cmd, shell=True, check=True)

# === 0. CREATION UTILISATEUR DEPLOY ===
def create_deploy_user():
    try:
        run(f"id -u {deploy_user}")
        print(f"✅ Utilisateur {deploy_user} existe déjà.")
    except subprocess.CalledProcessError:
        run(f"sudo adduser --disabled-password --gecos '' {deploy_user}")
        print(f"✅ Utilisateur {deploy_user} créé.")

    # Ajouter deploy dans le groupe www-data
    run(f"sudo usermod -aG www-data {deploy_user}")
    run(f"sudo usermod -aG sudo {deploy_user}")


    # Créer dossier .ssh pour deploy
    ssh_dir = f"/home/{deploy_user}/.ssh"
    run(f"sudo mkdir -p {ssh_dir}")
    run(f"sudo chown -R {deploy_user}:{deploy_user} {ssh_dir}")
    run(f"sudo chmod 700 {ssh_dir}")

    # Générer clé SSH si elle n'existe pas
    key_path = f"{ssh_dir}/id_ed25519"
    if not os.path.exists(key_path):
        run(f"sudo -u {deploy_user} ssh-keygen -t ed25519 -C '{deploy_user}@{domain}' -f {key_path} -N ''")
        print(f"\n📌 Clé publique SSH générée :\n")
        run(f"sudo cat {key_path}.pub")
        print("\n➡️  Ajoutez cette clé publique dans GitHub (Settings > Deploy keys ou SSH keys).")
    else:
        print("✅ Clé SSH déjà existante pour deploy.")
        run(f"sudo cat {key_path}.pub")
        print("\n➡️  Ajoutez cette clé publique dans GitHub (Settings > Deploy keys ou SSH keys).")

# === 1. INSTALLATION DES PACKAGES ===
def install_dependencies():
    run("sudo apt update && sudo apt upgrade -y")
    run("sudo apt install apache2 php php-mbstring php-xml php-bcmath php-mysql php-zip php-curl php-cli php-common php-gd unzip curl git composer libapache2-mod-php ufw certbot python3-certbot-apache mysql-server software-properties-common -y")
    run("sudo add-apt-repository ppa:ondrej/php")
    run("sudo apt install -y php8.3-fpm")
    run("sudo apt install -y fail2ban")
    run("sudo apt install aide -y")  # For automatic security updates


# === 2. INSTALLATION & CONFIGURATION MYSQL ===
def install_mysql():
    secure_sql = f"""
    ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '{mysql_root_password}';
    DELETE FROM mysql.user WHERE User='';
    DROP DATABASE IF EXISTS test;
    DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
    UPDATE mysql.user SET Host='localhost' WHERE User='root';
    FLUSH PRIVILEGES;
    """
    run(f"""sudo mysql -u root -p -e "{secure_sql}" """)

    # Créer la base de données et l'utilisateur Laravel (appuser)
    db_setup_sql = f"""
    CREATE DATABASE IF NOT EXISTS {mysql_db} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
    CREATE USER IF NOT EXISTS '{mysql_user}'@'localhost' IDENTIFIED BY '{mysql_password}';
    GRANT ALL PRIVILEGES ON {mysql_db}.* TO '{mysql_user}'@'localhost';
    FLUSH PRIVILEGES;
    """
    run(f"""mysql -uroot -p'{mysql_root_password}' -e "{db_setup_sql}" """) 

  #new

  
    more_db = input("Do you want more DATABASES ?: (y/n) ").strip()

    while more_db == "y":
        new_db_name = input("The DB name: ").strip()

        creatdb_sql_query = f"""
            CREATE DATABASE IF NOT EXISTS {new_db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
        """
        run(f""" mysql -uroot -p'{mysql_root_password}' -e "{creatdb_sql_query}" """)
        more_db = input("Do you want more DATABASES ?: (y/n) ").strip()




    more_user_account = input("Do you want  more user account ? (y/n): ").strip()


    while more_user_account == "y":
        username = input("The DB username: ").strip()
        userpassword = getpass.getpass("The password (invisible): ")
        allow_remote_access = input("Is it a remote user ? (y/n): ")
        access_scope =  "%" if allow_remote_access == "y" else "localhost"

        grant_to_dbs = input("Databases to access to. Note: separated by spaces. : ")
        dbs = grant_to_dbs.split()



        # l'utilisateur Laravel
        db_setup_sql = f"""
        CREATE USER IF NOT EXISTS '{username}'@'%' IDENTIFIED BY '{userpassword}';
        """
        run(f"""mysql -uroot -p'{mysql_root_password}' -e "{db_setup_sql}" """) 


        # grand db
        for index, db_name in enumerate(dbs):
            sql_q = f"""
            GRANT ALL PRIVILEGES ON {db_name}.* TO '{username}'@'{access_scope}';
            GRANT CREATE ROUTINE, CREATE, ALTER, ALTER ROUTINE, EXECUTE, DROP ON {db_name}.* TO '{username}'@'{access_scope}';
            FLUSH PRIVILEGES;
            """
            run(f"""mysql -uroot -p'{mysql_root_password}' -e "{sql_q}" """) 
        
        more_user_account = input("Do you want  more user account ? (y/n): ").strip()


 # end new
    # Enable MySQL remote access (optional)
    run(r"""sudo sed -i 's/bind-address\s*=\s*127.0.0.1/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf""")

    run("sudo systemctl restart mysql")
    
    

# === 3. CONFIGURATION DU FIREWALL ===
def configure_firewall():
    run("sudo ufw allow OpenSSH")
    run("sudo ufw allow 'Apache Full'")
    run("sudo ufw --force enable")

# === 4. CONFIGURATION DE FAIL2BAN ===
def configure_fail2ban():
    run("sudo systemctl enable fail2ban")
    run("sudo systemctl start fail2ban")

# === 4. CONFIGURATION DE FAIL2BAN ===
def configure_aide():
    run("sudo aide --config /etc/aide/aide.conf --init")
    run("sudo cp /var/lig/aide/aide.db.new /var/lib/aide/aide.db")

# === 5. CLONE DU PROJET AVEC DEPLOY ===
def clone_project():
    tmp_clone_dir = f"/home/{deploy_user}/{project_name}"
    run(f"sudo rm -rf {tmp_clone_dir}")
    run(f"sudo -u {deploy_user} git clone {git_repo} {tmp_clone_dir}")
    run(f"sudo rm -rf {project_dir}")
    run(f"sudo mv {tmp_clone_dir} {project_dir}")
    # Give deploy temporary ownership so composer can work
    run(f"sudo chown -R {deploy_user}:{deploy_user} {project_dir}")

# === 6. CONFIGURATION DES DROITS ===
def set_permissions():
    run(f"sudo chmod -R g+rw {project_dir}")
    run(f"sudo find {project_dir} -type d -exec chmod 2775 {{}} +")  # Setgid
    run(f"sudo find {project_dir} -type f -exec chmod 664 {{}} +")

# === 7. INSTALLATION DES DEPENDANCES LARAVEL ===
def install_laravel():
    run(f"sudo -u {deploy_user} composer install --no-interaction --prefer-dist --working-dir={project_dir}")
    run(f"sudo -u {deploy_user} cp {project_dir}/.env.example {project_dir}/.env")
    run(f"sudo -u {deploy_user} php {project_dir}/artisan key:generate")
    run(f"sudo chown -R {deploy_user}:www-data {project_dir}")

    # Mise à jour du .env
    env_path = os.path.join(project_dir, ".env")
    run(f"sudo chmod 664 {env_path}")
    with open(env_path, "r") as f:
        env = f.read()
    env = env.replace("APP_URL=http://localhost", f"APP_URL=https://{domain}")
    env = env.replace("DB_DATABASE=laravel", f"DB_DATABASE={mysql_db}")

    env = env.replace("DB_USERNAME=root", f"DB_USERNAME={mysql_user}")
    env = env.replace("DB_PASSWORD=", f"DB_PASSWORD={mysql_password}")
    with open(env_path, "w") as f:
        f.write(env)


# === 8. CONFIGURATION D'APACHE ===
def configure_apache():
    conf = f"""
<VirtualHost *:80>
    ServerAdmin webmaster@localhost
    ServerName {domain}
    DocumentRoot {project_dir}/public

    <Directory {project_dir}/public>
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${{APACHE_LOG_DIR}}/{project_name}_error.log
    CustomLog ${{APACHE_LOG_DIR}}/{project_name}_access.log combined
</VirtualHost>
"""
    with open(f"{project_name}.conf", "w") as f:
        f.write(conf)

    run(f"sudo mv {project_name}.conf /etc/apache2/sites-available/")
    run(f"sudo a2ensite {project_name}.conf")
    run("sudo a2dissite 000-default.conf")
    run("sudo a2enmod rewrite")
    run("sudo systemctl reload apache2")

# === 9. CONFIGURATION HTTPS ===
def enable_https():
    run(f"sudo certbot --apache -d {domain} --non-interactive --agree-tos -m admin@{domain}")
    run("sudo systemctl reload apache2")

# === DEPLOIEMENT COMPLET ===
def deploy():
    create_deploy_user()
    install_dependencies()
    install_mysql()
    configure_firewall()
    configure_fail2ban()
    clone_project()
    set_permissions()
    install_laravel()
    configure_apache()
    enable_https()
    print(f"\n✅ Déploiement terminé ! Visitez https://{domain}")

# === MAIN ===
if __name__ == "__main__":
    deploy()