import os
import subprocess
import getpass

# === PROMPTS UTILISATEUR ===
project_name = input("🔧 Project name : ").strip()
domain = input("🌐 DOMAINE NAME OR IP ADDR (ex: monsite.com) : ").strip()
git_repo = input("📦  Git REPOT(HTTPS ou SSH) : ").strip()
mysql_db = project_name #input("🛢️  DATABASE NAME : ").strip()
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
    run("sudo apt install software-properties-common -y")
    run("sudo add-apt-repository ppa:ondrej/php")
    run("sudo apt update")
    run("sudo apt install apache2 php7.4 php7.4-cli php7.4-fpm php7.4-mysql php7.4-xml php7.4-mbstring php7.4-curl php7.4-zip php7.4-intl php7.4-gd unzip curl git libapache2-mod-php7.4 ufw certbot python3-certbot-apache mysql-server -y")
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

    # Créer la base de données et l'utilisateur Codeigniter (appuser)
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



        # l'utilisateur app
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
    run("sudo ufw allow 3306/tcp")
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

# === 7. INSTALLATION et configuration ===
def install_codeigniter3():
  
    run(f"sudo chown -R {deploy_user}:www-data {project_dir}")

    run(f"sudo -u {deploy_user} cp {project_dir}/application/config/config.example.php {project_dir}/application/config/config.php")
    run(f"sudo -u {deploy_user} cp {project_dir}/application/config/database.example.php {project_dir}/application/config/database.php")

    # Mise à jour du config.php
    config_path = os.path.join(f"{project_dir}/application/config", "config.php")
    run(f"sudo chmod 664 {config_path}")
    with open(config_path, "r") as f:
        config = f.read()
    config = config.replace("$config['base_url'] = 'https://';", f"$config['base_url'] = 'https://{domain}';")
    config = config.replace("$config['index_page'] = 'index.php';", f"$config['index_page'] = '';")


    with open(config_path, "w") as f:
        f.write(config)


    # Mise à jour du database.php
    database_path = os.path.join(f"{project_dir}/application/config", "database.php")
    run(f"sudo chmod 664 {database_path}")
    with open(database_path, "r") as f:
        database = f.read()
    database = database.replace("$db['default']['username'] = 'root';", f"$db['default']['username'] = '{mysql_user}';")
    database = database.replace("$db['default']['password'] = '';", f"$db['default']['password'] = '{mysql_password}';")
    database = database.replace("$db['default']['database'] = 'codeigniter';", f"$db['default']['database'] = '{mysql_db}';")
    with open(database_path, "w") as f:
        f.write(database)



# === 8. CONFIGURATION D'APACHE ===
def configure_apache():
    conf = f"""
<VirtualHost *:80>
    ServerAdmin ousmanejrsylla@hotmail.com
    ServerName {domain}
    DocumentRoot {project_dir}

    # Redirect HTTP to HTTPS
    Redirect permanent / https://{domain}/

    <Directory {project_dir}>
       Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${{APACHE_LOG_DIR}}/{project_name}_error.log
    CustomLog ${{APACHE_LOG_DIR}}/{project_name}_access.log combined
RewriteEngine on
RewriteCond %{{SERVER_NAME}} ={domain}
RewriteRule ^ https://%{{SERVER_NAME}}%{{REQUEST_URI}} [END,NE,R=permanent]
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
    configure_fail2ban()
    clone_project()
    set_permissions()
    install_codeigniter3()
    configure_apache()
    enable_https()
    configure_firewall()

    print(f"\n✅ Déploiement terminé ! Visitez https://{domain}")

# === MAIN ===
if __name__ == "__main__":
    deploy()