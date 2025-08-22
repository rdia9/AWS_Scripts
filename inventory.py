import boto3
import csv
import os

# Initialize AWS clients
sts_client = boto3.client('sts')
org_client = boto3.client('organizations')

def assume_role(account_id, role_name="AssumeRole_ReadOnlyAccess"):
    """Assume a role in the given account and return temporary credentials."""
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    assumed_role = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName="assumed-role-session"
    )
    return assumed_role['Credentials']

def get_resource_tagging(credentials, resource_types):
    """Retrieve tagged resources from the specified account using temporary credentials."""
    tagging_client = boto3.client(
        'resourcegroupstaggingapi',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        region_name='eu-west-1'
    )
    resources = []
    paginator = tagging_client.get_paginator('get_resources')
    for page in paginator.paginate(ResourceTypeFilters=resource_types):
        resources.extend(page['ResourceTagMappingList'])
    return resources

def get_all_accounts():
    """Retrieve all active AWS accounts in the organization."""
    accounts = []
    paginator = org_client.get_paginator('list_accounts')
    for page in paginator.paginate():
        for account in page['Accounts']:
            if account['Status'] == 'ACTIVE':
                accounts.append(account['Id'])
    return accounts

def main():
    resource_types = [
        "s3", "dynamodb", "cloudformation", "ecs", "elasticloadbalancing",
        "acm", "elasticache", "sns", "events", "lambda", "rds", "glacier",
        "kms", "es", "ec2:eip", "ec2:instance", "ec2:internetgateway",
        "ec2:natgateway", "ec2:securitygroup", "ec2:subnet", "ec2:vpc", "ec2:volume"
    ]

    accounts = get_all_accounts()
    report = []

    for account_id in accounts:
        credentials = assume_role(account_id)
        resources = get_resource_tagging(credentials, resource_types)

        for resource in resources:
            arn = resource['ResourceARN']
            tags = {tag['Key']: tag['Value'] for tag in resource.get('Tags', [])}

            # Avoid snapshot resources
            if "snapshot" not in arn:
                report.append({
                    'Account': account_id,
                    'Service': arn.split(":")[2],
                    'Type': arn.split(":")[5] if ":" in arn else 'N/A',
                    'ResourceName': arn.split("/")[-1],
                    'Name': tags.get('Name', 'N/A'),
                    'Environment': tags.get('Environment', 'N/A'),
                    'Project': tags.get('Project', 'N/A'),
                    'App': tags.get('App', 'N/A'),
                    'Owner': tags.get('Owner', 'N/A'),
                    'Critical_app': tags.get('Critical_app', 'N/A'),
                    'Critical_service': tags.get('Critical_service', 'N/A'),
                    'Backup_Daily': tags.get('backup_daily', 'N/A'),
                    'Backup_Monthly': tags.get('backup_monthly', 'N/A'),
                    'StartStop': tags.get('StartStop', 'N/A'),
                    'ARN': arn
                })

    # Write report to CSV file in the current working directory
    file_path = os.path.join(os.getcwd(), "reportServices.csv")
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=[
            'Service', 'Type', 'ResourceName', 'Name', 'Environment', 'Project',
            'App', 'Owner', 'Critical_app', 'Critical_service', 'Backup_Daily',
            'Backup_Monthly', 'StartStop', 'ARN', 'Account'
        ])
        writer.writeheader()
        writer.writerows(report)

    print(f"Report generated and saved to {file_path}")

if __name__ == "__main__":
    main()
