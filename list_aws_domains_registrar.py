""" Script pour lister les domaines enregistrés dans AWS Route53 """


import csv
from datetime import datetime, timezone
import boto3
from botocore.exceptions import (
    ClientError,
    ParamValidationError,
    NoCredentialsError,
    PartialCredentialsError)

# Nom du rôle à assumer dans chaque compte
ASSUME_ROLE_NAME = "AssumeRole_ReadOnlyAccess"

# Génération du nom de fichier de sortie avec la date du jour
date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
OUTPUT_FILE = f"{date_str}_aws_domains_registrar.csv"


def assume_role(account_id, role_name):
    """
    Fonction pour assumer un rôle IAM dans un compte donné afin
    d'obtenir des credentials temporaires pour appeler Route53Domains.
    """
    sts = boto3.client("sts")
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    try:
        creds = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="ListDomainsSession"
        )["Credentials"]

        return boto3.client(
            "route53domains",
            region_name="us-east-1",  # Service global, exposé uniquement ici
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        )
    except (ClientError, ParamValidationError, NoCredentialsError, PartialCredentialsError) as e:
        print(f"[{account_id}] Impossible d'assumer le rôle: {e}")
        return None


def list_domains_for_account(account_id):
    """
    Fonction pour lister les domaines enregistrés dans un compte AWS
    via l’API Route53Domains.
    """
    client = assume_role(account_id, ASSUME_ROLE_NAME)
    if not client:
        return []

    domains = []
    try:
        paginator = client.get_paginator("list_domains")
        for page in paginator.paginate():
            for d in page["Domains"]:
                domains.append({
                    "AccountId": account_id,
                    "DomainName": d["DomainName"],
                    "AutoRenew": d.get("AutoRenew", False),
                    "TransferLock": d.get("TransferLock", False),
                    "Expiry": d.get("Expiry", ""),
                })
    except ClientError as e:
        print(f"[{account_id}] Erreur lors de la récupération des domaines: {e}")

    return domains


def main():
    """
    Fonction principale : parcourt tous les comptes de l’organisation,
    récupère la liste des domaines enregistrés et exporte le résultat en CSV.
    """
    org = boto3.client("organizations")
    accounts = []

    # Pagination pour récupérer tous les comptes
    paginator = org.get_paginator("list_accounts")
    for page in paginator.paginate():
        accounts.extend(page["Accounts"])

    all_domains = []

    for acc in accounts:
        account_id = acc["Id"]
        print(f"🔎 Traitement du compte {account_id} ({acc['Name']})")
        all_domains.extend(list_domains_for_account(account_id))

    # Écriture CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["AccountId", "DomainName", "AutoRenew", "TransferLock", "Expiry"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_domains)

    print(f"\n✅ Export terminé : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
