with import <nixpkgs> {};

stdenv.mkDerivation {
name = "python-env";

buildInputs = [
    python310
    python310Packages.pip
    python310Packages.virtualenv
    postgresql
    lighttpd
];

SOURCE_DATE_EPOCH = 315532800;
PROJDIR = "/tmp/python-dev";

shellHook = ''
    echo "Using ${python310.name}"
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib"
    
    [ ! -d '$PROJDIR' ] && virtualenv $PROJDIR && echo "SETUP python-dev: DONE"
    source $PROJDIR/bin/activate
    export LC_ALL=C

    pip install 'apache-airflow==2.8.3' --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.3/constraints-3.10.txt"
    pip install apache-airflow-providers-docker
    pip install avmesos psycopg2 waitress
    make install-dev

    mkdir /tmp/airflow
    mkdir /tmp/postgresql
    mkdir /tmp/dags
    mkdir /home/$USER/airflow

    initdb -D /tmp/postgresql
    cp docs/nixshell/pg_hba.conf /tmp/postgresql
    pg_ctl -D /tmp/postgresql -l logfile -o "--unix_socket_directories='/tmp' --listen_addresses='*'" start
    createuser -h /tmp -s airflow 
    createdb -h /tmp airflow -O airflow
    cp docs/examples/airflow.cfg /home/$USER/airflow/
    cp docs/examples/dags/* /tmp/dags/
    cp docs/nixshell/lighttpd.conf /tmp/
    airflow db migrate
    airflow users create --username admin --role Admin -e test@example.com -f admin -l admin --password admin

    # Webserver listen on 8881
    lighttpd -f /tmp/lighttpd.conf
    # airflow listen on 8880
    nohup airflow webserver &
# airflow scheduler
    '';
}
