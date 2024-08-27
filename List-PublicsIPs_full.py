import boto3
import csv

# Créer une session AWS par défaut (basée sur les variables d'environnement)
def get_default_session():
    session = boto3.Session()
    return session

# Récupérer la liste des comptes dans l'organisation AWS
def get_accounts():
    org_client = boto3.client('organizations')
    response = org_client.list_accounts()
    return response['Accounts']

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
    ips = []
    response = elb_client.describe_load_balancers()
    for load_balancer in response['LoadBalancerDescriptions']:
        ips.append({
            'Type': 'Classic Load Balancer',
            'ResourceId': load_balancer['LoadBalancerName'],
            'PublicIP': load_balancer['DNSName']
        })
    return ips

# Récupérer les IPs des Application/Network Load Balancers (ELBv2)
def get_elbv2_ips(elbv2_client):
    ips = []
    response = elbv2_client.describe_load_balancers()
    for load_balancer in response['LoadBalancers']:
        if 'DNSName' in load_balancer:
            ips.append({
                'Type': 'Application/Network Load Balancer',
                'ResourceId': load_balancer['LoadBalancerArn'],
                'PublicIP': load_balancer['DNSName']
            })
    return ips

# Récupérer les IPs des instances RDS
def get_rds_ips(rds_client):
    ips = []
    response = rds_client.describe_db_instances()
    for db_instance in response['DBInstances']:
        if 'Endpoint' in db_instance and 'Address' in db_instance['Endpoint']:
            ips.append({
                'Type': 'RDS',
                'ResourceId': db_instance['DBInstanceIdentifier'],
                'PublicIP': db_instance['Endpoint']['Address']
            })
    return ips

# Récupérer les IPs des instances DocumentDB
def get_docdb_ips(docdb_client):
    ips = []
    response = docdb_client.describe_db_instances()
    for db_instance in response['DBInstances']:
        if 'Endpoint' in db_instance and 'Address' in db_instance['Endpoint']:
            ips.append({
                'Type': 'DocumentDB',
                'ResourceId': db_instance['DBInstanceIdentifier'],
                'PublicIP': db_instance['Endpoint']['Address']
            })
    return ips

# Récupérer les IPs des clusters ElastiCache
def get_elasticache_ips(elasticache_client):
    ips = []
    response = elasticache_client.describe_cache_clusters(ShowCacheNodeInfo=True)
    for cluster in response['CacheClusters']:
        for node in cluster['CacheNodes']:
            if 'Endpoint' in node and 'Address' in node['Endpoint']:
                ips.append({
                    'Type': 'ElastiCache',
                    'ResourceId': cluster['CacheClusterId'],
                    'PublicIP': node['Endpoint']['Address']
                })
    return ips

# Récupérer les IPs des instances Lightsail
def get_lightsail_ips(lightsail_client):
    ips = []
    response = lightsail_client.get_instances()
    for instance in response['instances']:
        if 'publicIpAddress' in instance:
            ips.append({
                'Type': 'Lightsail',
                'ResourceId': instance['name'],
                'PublicIP': instance['publicIpAddress']
            })
    return ips

# Récupérer les IPs des API Gateway
def get_apigateway_ips(apigateway_client):
    ips = []
    response = apigateway_client.get_rest_apis()
    for api in response['items']:
        ips.append({
            'Type': 'API Gateway',
            'ResourceId': api['id'],
            'PublicIP': api['id'] + ".execute-api.amazonaws.com"  # API Gateway DNS
        })
    return ips

# Récupérer les IPs des distributions CloudFront
def get_cloudfront_ips(cloudfront_client):
    ips = []
    response = cloudfront_client.list_distributions()
    if 'DistributionList' in response:
        for distribution in response['DistributionList'].get('Items', []):
            ips.append({
                'Type': 'CloudFront',
                'ResourceId': distribution['Id'],
                'PublicIP': distribution['DomainName']
            })
    return ips

# Récupérer les IPs des services App Runner
def get_apprunner_ips(apprunner_client):
    ips = []
    response = apprunner_client.list_services()
    for service in response['ServiceSummaryList']:
        ips.append({
            'Type': 'App Runner',
            'ResourceId': service['ServiceArn'],
            'PublicIP': service['ServiceUrl']
        })
    return ips

# Récupérer les IPs des clusters EKS
def get_eks_ips(eks_client):
    ips = []
    response = eks_client.list_clusters()
    for cluster_name in response['clusters']:
        cluster_info = eks_client.describe_cluster(name=cluster_name)
        if 'endpoint' in cluster_info['cluster']:
            ips.append({
                'Type': 'EKS',
                'ResourceId': cluster_name,
                'PublicIP': cluster_info['cluster']['endpoint']
            })
    return ips

# Lister toutes les adresses IP publiques dans chaque compte
def list_public_ips_for_account():
    session = get_default_session()

    ec2_client = session.client('ec2')
    elb_client = session.client('elb')
    elbv2_client = session.client('elbv2')
    rds_client = session.client('rds')
    docdb_client = session.client('docdb')
    elasticache_client = session.client('elasticache')
    lightsail_client = session.client('lightsail')
    apigateway_client = session.client('apigateway')
    cloudfront_client = session.client('cloudfront')
    apprunner_client = session.client('apprunner')
    eks_client = session.client('eks')

    ips = []
    ips.extend(get_ec2_public_ips(ec2_client))
    ips.extend(get_elastic_ips(ec2_client))
    ips.extend(get_nat_gateway_ips(ec2_client))
    ips.extend(get_classic_elb_ips(elb_client))
    ips.extend(get_elbv2_ips(elbv2_client))
    ips.extend(get_rds_ips(rds_client))
    ips.extend(get_docdb_ips(docdb_client))
    ips.extend(get_elasticache_ips(elasticache_client))
    ips.extend(get_lightsail_ips(lightsail_client))
    ips.extend(get_apigateway_ips(apigateway_client))
    ips.extend(get_cloudfront_ips(cloudfront_client))
    ips.extend(get_apprunner_ips(apprunner_client))
    ips.extend(get_eks_ips(eks_client))

    return ips

# Liste des comptes dans votre organisation
accounts = get_accounts()

# Fichier de sortie
with open('public_ips.csv', 'w', newline='') as csvfile:
    fieldnames = ['AccountId', 'AccountName', 'ResourceType', 'ResourceId', 'PublicIP']
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
                    'AccountName': account_name,
                    'ResourceType': ip_info['Type'],
                    'ResourceId': ip_info['ResourceId'],
                    'PublicIP': ip_info['PublicIP']
                })
            print(f"Adresses IP récupérées pour le compte {account_name}")
        except Exception as e:
            print(f"Erreur lors de la récupération des IPs pour le compte {account_name} : {e}")
