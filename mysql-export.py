#!/usr/bin/python3
#-*- coding: utf-8 -*-

# This script is used to export MySQL databases and users to a directory.
# The script will generate a SQL file for each database and a SQL file for all users.
# The script will also generate a shell script to import the databases and users.
# The script will also compress the generated SQL files.

import os,sys,argparse,subprocess,logging
from collections import namedtuple
import MySQLdb

User = namedtuple("User", ["name", "host"])
UserAuth = namedtuple("UserAuth", ["password", "plugin"])

# Considering that Python 3.6 still does not support type hints for class variables, we will use a class to store the database information.
class Database:
    def __init__(self, name, charset, collation) -> None:
        self.name = name
        self.charset = charset
        self.collation = collation
        self.users = set()

def get_databases(db, database_exclude):
    databases:dict[str,Database] = {}
    with db.cursor() as cursor:
        query = "select schema_name,default_character_set_name,default_collation_name from information_schema.schemata where schema_name not in ('mysql','information_schema','performance_schema','sys')"
        cursor.execute(query)
        result = cursor.fetchall()
        for row in result:
            database, charset, collation = row[0], row[1], row[2]
            if database not in database_exclude: 
                databases[database] = Database(database, charset, collation)

        cursor.execute("select Db,User,Host,Select_priv,Insert_priv,Update_priv,Delete_priv,Create_priv,Drop_priv,Grant_priv,References_priv,Index_priv,Alter_priv,Create_tmp_table_priv,Lock_tables_priv,Create_view_priv,Show_view_priv,Create_routine_priv,Alter_routine_priv,Execute_priv,Event_priv,Trigger_priv,Delete_history_priv from db")
        result = cursor.fetchall()
        for row in result:
            database = row[0]
            if database not in databases: continue
            user = User(row[1], row[2])
            #else
            databases[database].users.add(user)
    return databases

def determine_hash_algo(password):
    if password.startswith("*") or password == "": return "mysql_native_password"
    if password.startswith("$"): return "caching_sha2_password"
    if len(password) == 16: return "mysql_old_password" # Not supported by MySQL >=8.0
    #else
    raise Exception("unknown password hash: %s" % password) # TODO: support more hash algorithms

def get_users(db):
    users:dict[User,UserAuth] = {}
    with db.cursor() as cursor:
        # check existance of password, plugin, authentication_string columns
        cursor.execute("show columns from user where Field in ('Password','plugin','authentication_string')")
        columns = [row[0].lower() for row in cursor.fetchall()]
        has_password = "password" in columns

        if has_password:
            logging.debug("Using password column")
            cursor.execute("select User,Host,Password from user where exists(select * from db where User=user.User and Host=user.Host)")
            result = cursor.fetchall()
            for row in result:
                user = User(row[0], row[1])
                password = row[2]
                if user not in users: users[user] = UserAuth(password, determine_hash_algo(password))
        else:
            logging.debug("Using plugin authentication as no password column found")
            cursor.execute("select User,Host,plugin,authentication_string from user where exists(select * from db where User=user.User and Host=user.Host)")
            result = cursor.fetchall()
            for row in result:
                user = User(row[0], row[1])
                plugin, password = row[2], row[3]
                if user not in users: users[user] = UserAuth(password, plugin)
    return users

def dump_database(host, root_user, root_password, database:Database, filename, no_content):
    with open(filename, "w") as f:
        print("DROP DATABASE IF EXISTS `%s`;" % database.name, file=f)
        print("CREATE DATABASE `%s` character set %s collate %s;" % (database.name, database.charset, database.collation), file=f)

        for user in database.users:
            print("GRANT ALL PRIVILEGES ON `%s`.* TO '%s'@'%s';" % (database.name, user.name, user.host), file=f)

        print("USE `%s`;" % database.name, file=f)
        f.flush()
        if not no_content:
            subprocess.check_call(["mysqldump", "--skip-extended-insert", "-h", host, "-u", root_user, "-p" + root_password, database.name], stdout=f)

def main(host, root_user, root_password, database_exclude, output_dir, no_content):
    # Open database connection
    db = MySQLdb.connect(host=host, user=root_user, passwd=root_password, db="mysql")
    try:
        users = get_users(db)
        databases = get_databases(db, database_exclude)
    finally:
        db.close()

    if not os.path.isdir(output_dir):
        raise Exception("output directory %s does not exist" % output_dir)

    with open(os.path.join(output_dir, "00users.sql"), "w") as f:
        logging.info("generating user creation script 00users.sql")
        for user, user_auth in users.items():
            print("DROP USER IF EXISTS '%s'@'%s';" % (user.name, user.host), file=f)
            print("CREATE USER '%s'@'%s' IDENTIFIED WITH '%s' AS '%s';" % (user.name, user.host, user_auth.plugin, user_auth.password), file=f)

    for database in databases.values():
        filename = os.path.join(output_dir, database.name + ".sql")
        logging.info("exporting database %s to %s" % (database.name, filename))
        dump_database(host, root_user, root_password, database, filename, no_content)
        logging.info("compressing %s" % filename)
        subprocess.check_call(["gzip", "-f", filename])

    with open(os.path.join(output_dir, "import.sh"), "w") as f:
        logging.info("generating import script import.sh")
        print("#!/bin/sh", file=f)
        print("set -e", file=f)
        print("MYSQL_ARGS='-u root'", file=f)
        print("mysql $MYSQL_ARGS < 00users.sql", file=f)
        for database in databases.keys():
            print("gunzip -c %s.sql.gz | mysql $MYSQL_ARGS" % (database, ), file=f)

    return 0

if __name__ == '__main__':
    # parse arguments
    parser = argparse.ArgumentParser(description='Migrate MySQL database')
    parser.add_argument("--host", help="MySQL host", default="localhost")
    parser.add_argument("--user", help="MySQL user", default="root")
    parser.add_argument("--password", help="MySQL password", default="")
    # -=database-exclude can be given multiple times
    parser.add_argument("--database-exclude", help="Database to exclude", action='append', default=[])
    parser.add_argument("--no-content", help="Do not export database content", action='store_true')
    tty = sys.stdout.isatty()
    parser.add_argument("--output-dir", help="Output directory", default="./mysql-export" if tty else None, required=not tty)
    parser.add_argument("--log-level", help="Log level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    sys.exit(main(args.host, args.user, args.password, args.database_exclude, args.output_dir, args.no_content))
