import boto3
import csv
import os
from datetime import datetime
import tempfile
import json

ORG_CLIENT = boto3.client('organizations')
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
ROLE_NAME = os.environ.get('ROLE_NAME', 'AssumeRole_ReadOnlyAccess')
UNSUPPORTED_RUNTIMES = ['python3.9', 'python3.8', 'python3.7', 'python3.6', 'python3.5', 'python3.4']
REGIONS = ['eu-west-1', 'eu-west-3', 'eu-north-1', 'us-east-1']  # Add more as needed

def assume_role(account_id):
    sts = boto3.client('sts')
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
    response = sts.assume_role(RoleArn=role_arn, RoleSessionName='LambdaAudit')
    creds = response['Credentials']
    return creds

def list_lambdas_for_account(account_id, account_name):
    lambdas_info = []
    creds = assume_role(account_id)
    for region in REGIONS:
        lambda_client = boto3.client(
            'lambda',
            region_name=region,
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken']
        )
        paginator = lambda_client.get_paginator('list_functions')
        for page in paginator.paginate():
            for func in page['Functions']:
                runtime = func.get('Runtime', '')
                if runtime in UNSUPPORTED_RUNTIMES:
                    lambdas_info.append({
                        'AccountName': account_name,
                        'AccountId': account_id,
                        'FunctionName': func['FunctionName'],
                        'Runtime': runtime,
                        'ARN': func['FunctionArn']
                    })
    return lambdas_info

def get_active_accounts():
    paginator = ORG_CLIENT.get_paginator('list_accounts')
    accounts = []
    for page in paginator.paginate():
        for acct in page['Accounts']:
            if acct['Status'] == 'ACTIVE':
                accounts.append({'Id': acct['Id'], 'Name': acct['Name']})
    return accounts

def lambda_handler(event, context):
    accounts = get_active_accounts()
    results = []
    for account in accounts:
        results.extend(list_lambdas_for_account(account['Id'], account['Name']))

    now = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"lambda-python39-audit-{now}.csv"
    filepath = os.path.join(tempfile.gettempdir(), filename)

    with open(filepath, 'w', newline='') as csvfile:
        fieldnames = ['AccountName', 'AccountId', 'FunctionName', 'Runtime', 'ARN']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    sns = boto3.client('sns')
    with open(filepath, 'r') as f:
        content = f.read()

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="Audit des fonctions Lambda en Python <= 3.9",
        Message=f"Voici les fonctions Lambda utilisant Python <= 3.9:\n\n{content}"
    )

    return {
        'statusCode': 200,
        'body': json.dumps(f"Audit terminé. {len(results)} fonctions détectées.")
    }
