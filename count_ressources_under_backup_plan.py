import boto3
from botocore.exceptions import NoCredentialsError, ClientError

def list_organization_accounts():
    org_client = boto3.client('organizations')
    accounts = []
    paginator = org_client.get_paginator('list_accounts')

    for page in paginator.paginate():
        accounts.extend(page['Accounts'])

    return accounts

def assume_role(account_id, role_name):
    sts_client = boto3.client('sts')

    # Assume le rôle dans le compte cible
    response = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
        RoleSessionName="BackupProtectedResourcesSession"
    )

    # Retourner les credentials pour la session
    return response['Credentials']

def count_protected_resources_in_account(credentials=None):
    try:
        if credentials:
            # Si nous avons des credentials temporaires, les utiliser pour la session
            backup_client = boto3.client(
                'backup',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
        else:
            # Utiliser la session par défaut pour le compte root
            backup_client = boto3.client('backup')

        # Paginator pour lister les ressources protégées
        paginator = backup_client.get_paginator('list_protected_resources')
        resource_count = 0

        for page in paginator.paginate():
            # Compter le nombre de ressources protégées
            resource_count += len(page['Results'])

        return resource_count

    except (NoCredentialsError, ClientError) as e:
        print(f"Erreur lors de l'accès aux ressources protégées: {str(e)}")
        return 0

if __name__ == "__main__":
    # Liste des comptes de l'organisation via AWS Organizations
    accounts = list_organization_accounts()

    total_resources = 0
    role_name = "OrganizationAccountAccessRole"  # Rôle utilisé pour accéder aux comptes membres
    for account in accounts:
        account_id = account['Id']
        account_status = account['Status']

        # Vérifier que le compte est actif avant de l'interroger
        if account_status == 'ACTIVE':
            print(f"Comptage des ressources protégées pour le compte {account_id}...")

            if account_id == boto3.client('sts').get_caller_identity()['Account']:
                # Si c'est le compte root, ne pas assumer un rôle, utiliser la session actuelle
                resources_in_account = count_protected_resources_in_account()
            else:
                # Assumer le rôle dans les autres comptes membres
                credentials = assume_role(account_id, role_name)
                resources_in_account = count_protected_resources_in_account(credentials)

            print(f"Nombre de ressources protégées dans le compte {account_id}: {resources_in_account}")

            total_resources += resources_in_account

    print(f"Nombre total de ressources protégées dans toute l'organisation: {total_resources}")
