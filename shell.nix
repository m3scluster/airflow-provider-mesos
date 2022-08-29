with import <nixpkgs> {};

stdenv.mkDerivation {
name = "python-env";

buildInputs = [
    python37
    python37Packages.pip
    python37Packages.virtualenv
    postgresql
    lighttpd
];

SOURCE_DATE_EPOCH = 315532800;
PROJDIR = "${toString ./.}";

shellHook = ''
    echo "Using ${python37.name}"

    [ ! -d '$PROJDIR/python-dev' ] && virtualenv python-dev && echo "SETUP python-dev: DONE"
    source python-dev/bin/activate
    pip install 'apache-airflow==2.1.2' --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.1.2/constraints-3.7.txt"     
    pip install avmesos psycopg2 waitress apache-airflow-providers-docker
    make install-dev

    mkdir /tmp/airflow
    mkdir /tmp/dags
    mkdir /home/$USER/airflow

    export LC_ALL="C.utf8"
    export LC_CTYPE="C.utf8"
    initdb -D /tmp/airflow
    pg_ctl -D /tmp/airflow -l logfile -o "--unix_socket_directories='/tmp'" start
    createdb -h /tmp airflow
    cp docs/examples/airflow.cfg /home/$USER/airflow/
    cp docs/examples/dags/* /tmp/dags/
    cp docs/nixshell/lighttpd.conf /tmp/
    airflow db init
    airflow users create --username admin --role Admin -e test@example.com -f admin -l admin --password admin

    lighttpd -f /tmp/lighttpd.conf
    airflow webserver > /dev/null&
#airflow scheduler
    '';
}
