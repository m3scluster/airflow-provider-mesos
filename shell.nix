with import <nixpkgs> {};

stdenv.mkDerivation {
name = "python-env";

buildInputs = [
    python311
    python311Packages.pip
    python311Packages.virtualenv
    python311Packages.xmlsec
		python311Packages.psycopg2
    postgresql
    lighttpd
    jq
		libxml2
		pkg-config
];

SOURCE_DATE_EPOCH = 315532800;
PROJDIR = "/tmp/python-dev";
S_NETWORK="host";

shellHook = ''
    echo "Using ${python311.name}"
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib"

    [ ! -d '$PROJDIR' ] && virtualenv $PROJDIR && echo "SETUP python-dev: DONE"
    source $PROJDIR/bin/activate
    export LC_ALL=C

    pip install 'apache-airflow==2.10.1' --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.1/constraints-3.11.txt"
		pip install boto3 avmesos waitress
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
    airflow users create --username admin --role Admin -e test@example.com -f admin -l admin --password admin

    # Webserver listen on 8881
    lighttpd -f /tmp/lighttpd.conf
    # airflow listen on 8880
    nohup airflow webserver 2>&1>/dev/null &
#    nohup airflow scheduler 2>&1>/dev/null &
# airflow scheduler
    '';
}
