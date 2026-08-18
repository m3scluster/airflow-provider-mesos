with import <nixpkgs> {};

stdenv.mkDerivation {
name = "python-env";

buildInputs = [
		python312
		python312Packages.pip
		python312Packages.virtualenv
		python312Packages.xmlsec
		python312Packages.psycopg2
		python312Packages.python-lsp-server
		postgresql
		lighttpd
		jq
		libxml2
		pkg-config
		kdePackages.kate
];

SOURCE_DATE_EPOCH = 315532800;
PROJDIR = "/tmp/python-dev";
S_NETWORK = "weave";
S_HOSTNAME = "airflow.weave.local";


shellHook = ''
		echo "Using ${python312.name}"
		export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib"
		export PATH=/home/$USER/bin:$PATH

		[ ! -d '$PROJDIR' ] && virtualenv $PROJDIR && echo "SETUP python-dev: DONE"
		source $PROJDIR/bin/activate
		export LC_ALL=C

		pip install 'apache-airflow==3.2.2' --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.2.2/constraints-3.12.txt"
		pip install boto3 avmesos waitress asyncpg
		pip install apache-airflow-providers-docker
		pip install apache-airflow-providers-amazon
		make install-dev

		mkdir /tmp/airflow
		mkdir /tmp/postgresql
		mkdir /home/$USER/airflow

		initdb -D /tmp/postgresql
		cp docs/nixshell/pg_hba.conf /tmp/postgresql
		pg_ctl -D /tmp/postgresql -l logfile -o "--unix_socket_directories='/tmp' --listen_addresses='*'" start
		createuser -h /tmp -s airflow
		createdb -h /tmp airflow -O airflow
		cp docs/examples/airflow.cfg /home/$USER/airflow/
		cp -r docs/examples/aws /home/$USER/airflow/.aws
		cp docs/nixshell/lighttpd.conf /tmp/
		airflow db migrate
		airflow connections create-default-connections

		# Webserver listen on 8881
		lighttpd -f /tmp/lighttpd.conf
		# airflow listen on 8880
		nohup airflow api-server 2>&1>/dev/null &
		nohup airflow dag-processor 2>&1>/dev/null &
		sleep 10
    cat /home/$USER/airflow/simple_auth_manager_passwords.json.generated
		'';
}
