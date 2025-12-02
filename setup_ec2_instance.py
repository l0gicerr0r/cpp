"""
EC2 Instance Setup Script
Creates EC2 instance with security group for hosting Flask app
"""

import boto3
import time
import base64

# Configuration
AWS_REGION = 'eu-west-1'
ACCOUNT_ID = '565209206796'
KEY_PAIR_NAME = 'cloud-key-pair'
AMI_ID = 'ami-08b6a2983df6e9e25'  # Amazon Linux 2023
INSTANCE_TYPE = 't3.small'
SECURITY_GROUP_NAME = 'automotive-app-sg'
INSTANCE_NAME = 'automotive-flask-server'

# Initialize AWS clients
ec2 = boto3.client('ec2', region_name=AWS_REGION)
ec2_resource = boto3.resource('ec2', region_name=AWS_REGION)


def get_default_vpc():
    """Get default VPC ID"""
    response = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
    if response['Vpcs']:
        return response['Vpcs'][0]['VpcId']
    return None


def create_security_group():
    """Create security group for Flask app"""
    print(f"Creating security group: {SECURITY_GROUP_NAME}...")
    
    vpc_id = get_default_vpc()
    
    try:
        response = ec2.create_security_group(
            GroupName=SECURITY_GROUP_NAME,
            Description='Security group for Automotive Flask application',
            VpcId=vpc_id
        )
        security_group_id = response['GroupId']
        
        # Add inbound rules
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH access'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 5000,
                    'ToPort': 5000,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Flask app'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTPS'}]
                }
            ]
        )
        
        print(f"✓ Security group created: {security_group_id}")
        return security_group_id
        
    except ec2.exceptions.ClientError as e:
        if 'InvalidGroup.Duplicate' in str(e):
            # Get existing security group
            response = ec2.describe_security_groups(
                Filters=[{'Name': 'group-name', 'Values': [SECURITY_GROUP_NAME]}]
            )
            if response['SecurityGroups']:
                sg_id = response['SecurityGroups'][0]['GroupId']
                print(f"✓ Security group already exists: {sg_id}")
                return sg_id
        print(f"✗ Error creating security group: {e}")
        return None


def get_user_data_script():
    """Generate user data script for EC2 instance"""
    user_data = '''#!/bin/bash
# Update system
yum update -y

# Install Python 3.11 and pip
yum install -y python3.11 python3.11-pip git

# Create app directory
mkdir -p /home/ec2-user/automotive-app
cd /home/ec2-user/automotive-app

# Clone the repository
git clone https://github.com/l0gicerr0r/cpp.git .

# Install Python dependencies
pip3.11 install -r requirements.txt

# Set up environment variables
export FLASK_APP=app.py
export FLASK_ENV=production

# Change ownership
chown -R ec2-user:ec2-user /home/ec2-user/automotive-app

# Start Flask app with nohup
cd /home/ec2-user/automotive-app
nohup python3.11 app.py > /home/ec2-user/flask.log 2>&1 &

echo "Flask application started"
'''
    return base64.b64encode(user_data.encode()).decode()


def create_ec2_instance():
    """Create EC2 instance"""
    print("Creating EC2 instance...")
    
    security_group_id = create_security_group()
    if not security_group_id:
        print("✗ Failed to create/get security group")
        return None
    
    try:
        instances = ec2_resource.create_instances(
            ImageId=AMI_ID,
            MinCount=1,
            MaxCount=1,
            InstanceType=INSTANCE_TYPE,
            KeyName=KEY_PAIR_NAME,
            SecurityGroupIds=[security_group_id],
            UserData=get_user_data_script(),
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': INSTANCE_NAME},
                        {'Key': 'Project', 'Value': 'Automotive-App'}
                    ]
                }
            ]
        )
        
        instance = instances[0]
        print(f"✓ EC2 instance created: {instance.id}")
        
        # Wait for instance to be running
        print("Waiting for instance to start...")
        instance.wait_until_running()
        instance.reload()
        
        print(f"✓ Instance is running!")
        print(f"  Instance ID: {instance.id}")
        print(f"  Public IP: {instance.public_ip_address}")
        print(f"  Public DNS: {instance.public_dns_name}")
        
        return {
            'instance_id': instance.id,
            'public_ip': instance.public_ip_address,
            'public_dns': instance.public_dns_name,
            'security_group_id': security_group_id
        }
        
    except Exception as e:
        print(f"✗ Error creating EC2 instance: {e}")
        return None


def get_existing_instance():
    """Get existing instance if any"""
    try:
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': [INSTANCE_NAME]},
                {'Name': 'instance-state-name', 'Values': ['running', 'pending']}
            ]
        )
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                return {
                    'instance_id': instance['InstanceId'],
                    'public_ip': instance.get('PublicIpAddress'),
                    'public_dns': instance.get('PublicDnsName'),
                    'state': instance['State']['Name']
                }
        return None
    except Exception as e:
        print(f"Error checking existing instance: {e}")
        return None


def main():
    """Main function"""
    print("=" * 60)
    print("EC2 Instance Setup for Automotive Flask App")
    print("=" * 60)
    print(f"Region: {AWS_REGION}")
    print(f"AMI: {AMI_ID}")
    print(f"Instance Type: {INSTANCE_TYPE}")
    print(f"Key Pair: {KEY_PAIR_NAME}")
    print("=" * 60)
    
    # Check for existing instance
    existing = get_existing_instance()
    if existing:
        print(f"\n⚠ Existing instance found: {existing['instance_id']}")
        print(f"  State: {existing['state']}")
        print(f"  Public IP: {existing['public_ip']}")
        response = input("\nCreate new instance anyway? (y/n): ")
        if response.lower() != 'y':
            print("Using existing instance.")
            return existing
    
    # Create new instance
    result = create_ec2_instance()
    
    if result:
        print("\n" + "=" * 60)
        print("EC2 Setup Complete!")
        print("=" * 60)
        print(f"\nAccess your Flask app at:")
        print(f"  http://{result['public_ip']}:5000")
        print(f"\nSSH into the instance:")
        print(f"  ssh -i cloud-key-pair.pem ec2-user@{result['public_ip']}")
        print("\nNote: Wait a few minutes for the app to deploy after instance starts.")
        
        # Save instance details
        with open('ec2_instance_details.txt', 'w') as f:
            f.write(f"Instance ID: {result['instance_id']}\n")
            f.write(f"Public IP: {result['public_ip']}\n")
            f.write(f"Public DNS: {result['public_dns']}\n")
            f.write(f"Security Group: {result['security_group_id']}\n")
        print("\nInstance details saved to ec2_instance_details.txt")
    
    return result


if __name__ == '__main__':
    main()
