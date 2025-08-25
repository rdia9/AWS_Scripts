"""Module listant les customs domains pour une organisation"""

import boto3

# --- Config ---
ROLE_NAME = "AssumeRole_ReadOnlyAccess"  # rôle à assumer dans chaque compte
MAX_RESULTS = 60
REGION_LIST = ["eu-west-1", "eu-west-3", "us-east-1"]  # None pour auto-lister toutes les régions

# --- Fonctions ---
def list_accounts():
    """Fonction pour obtenir tous les comptes AWS de l'organisation via AWS Organizations."""
    org_client = boto3.client("organizations")
    accounts = []
    paginator = org_client.get_paginator("list_accounts")
    for page in paginator.paginate():
         for acc in page["Accounts"]:
            if acc["Status"] == "ACTIVE":  # Ignorer comptes désactivés
                accounts.append(acc)dan
    return accounts

def list_regions():
    """Fonction pour obtenir la liste de toutes les régions AWS disponibles."""
    ec2 = boto3.client("ec2")
    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]

def assume_role(account_id):
    """Fonction pour assumer un rôle dans un compte donné et obtenir des credentials temporaires.

    Args:
        account_id (str): ID du compte AWS dans lequel assumer le rôle.

    Returns:
        dict: Credentials temporaires (AccessKeyId, SecretAccessKey, SessionToken)
    """
    sts_client = boto3.client("sts")
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
    resp = sts_client.assume_role(RoleArn=role_arn, RoleSessionName="CognitoDomainScan")
    return resp["Credentials"]

def get_cognito_client(region, credentials):
    """Fonction pour créer un client Cognito IDP avec des credentials temporaires.

    Args:
        region (str): Région AWS.
        credentials (dict): Credentials temporaires STS.

    Returns:
        boto3.client: Client Cognito IDP
    """
    return boto3.client(
        "cognito-idp",
        region_name=region,
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"]
    )

def list_user_pools(cognito_client):
    """Fonction pour lister tous les User Pools d'un client Cognito dans une région.

    Args:
        cognito_client (boto3.client): Client Cognito IDP.

    Returns:
        list: Liste des dictionnaires représentant les User Pools.
    """
    pools = []
    paginator = cognito_client.get_paginator("list_user_pools")
    for page in paginator.paginate(MaxResults=MAX_RESULTS):
        pools.extend(page["UserPools"])
    return pools

def get_custom_domain(cognito_client, pool_id):
    """Fonction pour récupérer le custom domain d'un User Pool.

    Args:
        cognito_client (boto3.client): Client Cognito IDP.
        pool_id (str): ID du User Pool.

    Returns:
        str|None: Nom du custom domain si présent, sinon None.
    """
    try:
        response = cognito_client.describe_user_pool_domain(Domain=pool_id)
        return response.get("DomainDescription", {}).get("Domain")
    except cognito_client.exceptions.ResourceNotFoundException:
        return None

# --- Script principal ---
def main():
    """Fonction principale pour parcourir tous les comptes et régions, lister les User Pools et leurs Custom Domains."""
    accounts = list_accounts()
    regions = REGION_LIST if REGION_LIST else list_regions()
    result = []

    for account in accounts:
        account_id = account["Id"]
        account_name = account["Name"]
        print(f"\nScanning account {account_id} ({account_name})")
        creds = assume_role(account_id)

        for region in regions:
            print(f"  Region: {region}")
            cognito_client = get_cognito_client(region, creds)
            pools = list_user_pools(cognito_client)
            for pool in pools:
                pool_id = pool["Id"]
                pool_name = pool["Name"]
                # domain = get_custom_domain(cognito_client, pool_id)
                result.append({
                    "AccountId": account_id,
                    "AccountName": account_name,
                    "Region": region,
                    "UserPoolId": pool_id,
                    "UserPoolName": pool_name,
                    # "CustomDomain": domain
                })

    # --- Affichage ---
    print("\nUser Pools with Custom Domains:")
    for r in result:
        print(r)

if __name__ == "__main__":
    main()
