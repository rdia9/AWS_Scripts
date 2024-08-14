import boto3
import pandas as pd
from datetime import datetime

def list_aws_accounts():
    # Créer un client pour AWS Organizations
    client = boto3.client('organizations')

    # Initialiser une liste pour stocker les comptes
    accounts = []

    # Appeler l'API ListAccounts pour récupérer la liste des comptes
    try:
        paginator = client.get_paginator('list_accounts')
        for page in paginator.paginate():
            accounts.extend(page['Accounts'])

    except Exception as e:
        print(f"Erreur lors de l'extraction des comptes AWS : {e}")
        return []

    return accounts

def save_accounts_to_csv(accounts):
    # Obtenir la date du jour au format YYmmDD
    date_str = datetime.now().strftime("%Y%m%d")

    # Nom du fichier avec la date incluse
    filename = f"{date_str}_aws_accounts.csv"

    # Créer une liste de dictionnaires à partir des comptes
    accounts_data = [{
        'ID': account['Id'],
        'Nom': account['Name'],
        'Email': account['Email'],
        'État': account['Status'],
        'Date de création': account['JoinedTimestamp'].strftime('%Y-%m-%d %H:%M:%S')
    } for account in accounts]

    # Convertir en DataFrame
    df = pd.DataFrame(accounts_data)

    # Sauvegarder dans un fichier CSV
    df.to_csv(filename, index=False)
    print(f"Les comptes AWS ont été sauvegardés dans le fichier : {filename}")

def main():
    accounts = list_aws_accounts()
    if accounts:
        save_accounts_to_csv(accounts)
    else:
        print("Aucun compte trouvé ou une erreur s'est produite.")

if __name__ == "__main__":
    main()
