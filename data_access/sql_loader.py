from sqlalchemy import create_engine
import json
import os
import pandas as pd


def load_credentials():
    filepath = os.path.join(os.path.dirname(__file__), "config.json")
    with open(filepath, 'r') as file:
        return json.load(file)


def load_sql(sql_query):

        # Chargement des identifiants de connexion
        creds =  load_credentials()
        server = creds['server']
        database = creds['database']
        username = creds['username']
        password = creds['password']
        port = creds.get('port', 1433)
        
        # Connexion au serveur SQL
        connection_string = f"mssql+pyodbc://{username}:{password}@{server}:{port}/{database}?driver=SQL+Server"
        engine = create_engine(connection_string)
        
        # Transformation des données dans un dataframe pandas
        data = pd.read_sql(sql_query, engine)
        engine.dispose()
        
        return data
