import boto3
import csv

# Récupérer la liste des comptes dans l'organisation AWS
def get_accounts():
    org_client = boto3.client('organizations')
    response = org_client.list_accounts()
    return response['Accounts']

# Créer une session AWS par défaut (basée sur les variables d'environnement)
def get_default_session():
    session = boto3.Session()
    return session

# Récupérer les adresses IP publiques des instances EC2
def get_ec2_public_ips(ec2_client):
    ips = []
    response = ec2_client.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if 'PublicIpAddress' in instance:
                ips.append({
                    'Type': 'EC2',
                    'ResourceId': instance['InstanceId'],
                    'PublicIP': instance['PublicIpAddress']
                })
    return ips

# Récupérer les Elastic IPs
def get_elastic_ips(ec2_client):
    """Récupérer les Elastic IPs"""
    ips = []
    response = ec2_client.describe_addresses()
    for address in response['Addresses']:
        if 'PublicIp' in address:
            ips.append({
                'Type': 'Elastic IP',
                'ResourceId': address['AllocationId'],
                'PublicIP': address['PublicIp']
            })
    return ips

# Récupérer les NAT Gateways et leurs IPs
def get_nat_gateway_ips(ec2_client):
    """Récupérer les IPs des NAT Gateways"""
    ips = []
    response = ec2_client.describe_nat_gateways()
    for nat_gateway in response['NatGateways']:
        for address in nat_gateway.get('NatGatewayAddresses', []):
            if 'PublicIp' in address:
                ips.append({
                    'Type': 'NAT Gateway',
                    'ResourceId': nat_gateway['NatGatewayId'],
                    'PublicIP': address['PublicIp']
                })
    return ips

# Récupérer les IPs des Classic Load Balancers (ELB)
def get_classic_elb_ips(elb_client):
    """Récupérer les IPs des Classic Load Balancers (ELB)"""
    ips = []
    response = elb_client.describe_load_balancers()
    for load_balancer in response['LoadBalancerDescriptions']:
        ips.append({
            'Type': 'Classic Load Balancer',
            'ResourceId': load_balancer['LoadBalancerName'],
            'PublicIP': load_balancer['DNSName']  # DNS Name is used to resolve public IPs
        })
    return ips

# Récupérer les IPs des Application/Network Load Balancers (ELBv2)
def get_elbv2_ips(elbv2_client):
    """Récupérer les IPs des Application/Network Load Balancers (ELBv2)"""
    ips = []
    response = elbv2_client.describe_load_balancers()
    for load_balancer in response['LoadBalancers']:
        if 'DNSName' in load_balancer:
            ips.append({
                'Type': 'Application/Network Load Balancer',
                'ResourceId': load_balancer['LoadBalancerArn'],
                'PublicIP': load_balancer['DNSName']  # DNS Name is used to resolve public IPs
            })
    return ips

# Récupérer les IPs des instances DocumentDB
def get_docdb_ips(docdb_client):
    """Récupérer les IPs des instances DocumentDB"""
    ips = []
    response = docdb_client.describe_db_instances()
    for db_instance in response['DBInstances']:
        if 'Endpoint' in db_instance and 'Address' in db_instance['Endpoint']:
            ips.append({
                'Type': 'DocumentDB',
                'ResourceId': db_instance['DBInstanceIdentifier'],
                'PublicIP': db_instance['Endpoint']['Address']  # DNS Name used to resolve IP
            })
    return ips

# Lister toutes les adresses IP publiques dans chaque compte
def list_public_ips_for_account():
    """Récupérer les adresses IP publiques pour un compte AWS"""
    session = get_default_session()

    ec2_client = session.client('ec2')
    elb_client = session.client('elb')
    elbv2_client = session.client('elbv2')
    docdb_client = session.client('docdb')

    ips = []
    ips.extend(get_ec2_public_ips(ec2_client))
    ips.extend(get_elastic_ips(ec2_client))
    ips.extend(get_nat_gateway_ips(ec2_client))
    ips.extend(get_classic_elb_ips(elb_client))
    ips.extend(get_elbv2_ips(elbv2_client))
    ips.extend(get_docdb_ips(docdb_client))

    return ips

# Liste des comptes dans votre organisation
accounts = get_accounts()

# Fichier de sortie
with open('public_ips.csv', 'w', newline='') as csvfile:
    fieldnames = ['AccountId', 'ResourceType', 'ResourceId', 'PublicIP']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    # Parcourir chaque compte et récupérer les IPs publiques
    for account in accounts:
        account_id = account['Id']
        account_name = account['Name']

        try:
            # Récupérer les IP publiques pour ce compte
            print(f"Récupération des IPs pour le compte {account_name} ({account_id})...")
            account_ips = list_public_ips_for_account()
            for ip_info in account_ips:
                writer.writerow({
                    'AccountId': account_id,
                    'ResourceType': ip_info['Type'],
                    'ResourceId': ip_info['ResourceId'],
                    'PublicIP': ip_info['PublicIP']
                })
            print(f"Adresses IP récupérées pour le compte {account_name}")
        except Exception as e:
            print(f"Erreur pour le compte {account_name}: {e}")

print("Les adresses IP publiques ont été récapitulées dans public_ips.csv")
