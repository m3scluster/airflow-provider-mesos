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
PROJDIR = "${toString ./.}";

shellHook = ''
    echo "Using ${python38.name}"
    
    [ ! -d '$PROJDIR/python-dev' ] && virtualenv python-dev && echo "SETUP python-dev: DONE"
    source python-dev/bin/activate
    pip install 'apache-airflow==2.5.3' --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.5.3/constraints-3.10.txt"
    pip install apache-airflow-providers-docker
    pip install avmesos psycopg2 waitress
    make install-dev

    mkdir /tmp/airflow
    mkdir /tmp/dags
    mkdir /home/$USER/airflow

    initdb -D /tmp/airflow
    pg_ctl -D /tmp/airflow -l logfile -o "--unix_socket_directories='/tmp'" start
    createdb -h /tmp airflow
    cp docs/examples/airflow.cfg /home/$USER/airflow/
    cp docs/examples/dags/* /tmp/dags/
    cp docs/nixshell/lighttpd.conf /tmp/
    airflow db init
    airflow users create --username admin --role Admin -e test@example.com -f admin -l admin --password admin

    # Webserver listen on 8881
    lighttpd -f /tmp/lighttpd.conf
    # airflow listen on 8880
    nohup airflow webserver &
# airflow scheduler
    '';
}
