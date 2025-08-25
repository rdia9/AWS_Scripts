import boto3
import csv

# Nom du rôle à assumer dans chaque compte
ROLE_NAME = "AssumeRole_ReadOnlyAccess"

# Clients initiaux (dans le compte management)
org_client = boto3.client("organizations")
sts_client = boto3.client("sts")

# Récupérer tous les comptes actifs de l’organisation
accounts = []
paginator = org_client.get_paginator("list_accounts")
for page in paginator.paginate():
    for acct in page["Accounts"]:
        if acct["Status"] == "ACTIVE":
            accounts.append(acct["Id"])

print(f"Comptes trouvés : {len(accounts)}")

# Préparer CSV
with open("OrgCloudfront_distributions.csv", "w", newline="") as csvfile:
    fieldnames = ["AccountId", "DistributionId", "DomainName", "Comment", "Enabled"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for account_id in accounts:
        print(f"=== Compte {account_id} ===")
        try:
            # Assumer le rôle dans le compte cible
            role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
            creds = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName="ListCloudFront"
            )["Credentials"]

            # Créer client CloudFront avec credentials du compte
            cf_client = boto3.client(
                "cloudfront",
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
            )

            # Lister les distributions
            paginator = cf_client.get_paginator("list_distributions")
            for page in paginator.paginate():
                dist_list = page.get("DistributionList", {}).get("Items", [])
                for dist in dist_list:
                    writer.writerow({
                        "AccountId": account_id,
                        "DistributionId": dist["Id"],
                        "DomainName": dist["DomainName"],
                        "Comment": dist.get("Comment", ""),
                        "Enabled": dist["Enabled"]
                    })
        except Exception as e:
            print(f"Erreur dans le compte {account_id}: {e}")

