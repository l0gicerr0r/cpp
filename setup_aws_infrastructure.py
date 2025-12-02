"""
AWS Infrastructure Setup Script
Creates all required AWS resources for the Automotive Flask Application

Services Created:
1. S3 Bucket - For vehicle image storage
2. DynamoDB Table - For activity logging
3. Lambda Function - For serverless price analysis
4. CloudWatch Log Group - For application logging
5. SSM Parameters - For secrets management
"""

import boto3
import json
import time
import zipfile
import io

# Configuration
AWS_REGION = 'eu-west-1'
ACCOUNT_ID = '565209206796'
S3_BUCKET_NAME = f'automotive-app-images-{ACCOUNT_ID}'
DYNAMODB_TABLE_NAME = 'automotive-activity-logs'
LAMBDA_FUNCTION_NAME = 'automotive-price-analyzer'
CLOUDWATCH_LOG_GROUP = '/automotive-app/logs'
LAMBDA_ROLE_NAME = 'automotive-lambda-role'

# Initialize AWS clients
s3 = boto3.client('s3', region_name=AWS_REGION)
dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)
lambda_client = boto3.client('lambda', region_name=AWS_REGION)
logs = boto3.client('logs', region_name=AWS_REGION)
ssm = boto3.client('ssm', region_name=AWS_REGION)
iam = boto3.client('iam', region_name=AWS_REGION)


def create_s3_bucket():
    """Create S3 bucket for image storage"""
    print(f"Creating S3 bucket: {S3_BUCKET_NAME}...")
    try:
        s3.create_bucket(
            Bucket=S3_BUCKET_NAME,
            CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
        )
        
        # Enable public access for images
        s3.put_public_access_block(
            Bucket=S3_BUCKET_NAME,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        
        # Set bucket policy for public read
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{S3_BUCKET_NAME}/*"
            }]
        }
        s3.put_bucket_policy(Bucket=S3_BUCKET_NAME, Policy=json.dumps(bucket_policy))
        
        # Enable CORS
        cors_config = {
            'CORSRules': [{
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE'],
                'AllowedOrigins': ['*'],
                'MaxAgeSeconds': 3000
            }]
        }
        s3.put_bucket_cors(Bucket=S3_BUCKET_NAME, CORSConfiguration=cors_config)
        
        print(f"✓ S3 bucket created: {S3_BUCKET_NAME}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"✓ S3 bucket already exists: {S3_BUCKET_NAME}")
    except Exception as e:
        print(f"✗ Error creating S3 bucket: {e}")


def create_dynamodb_table():
    """Create DynamoDB table for activity logging"""
    print(f"Creating DynamoDB table: {DYNAMODB_TABLE_NAME}...")
    try:
        dynamodb.create_table(
            TableName=DYNAMODB_TABLE_NAME,
            KeySchema=[
                {'AttributeName': 'activity_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'activity_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Wait for table to be created
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=DYNAMODB_TABLE_NAME)
        
        print(f"✓ DynamoDB table created: {DYNAMODB_TABLE_NAME}")
    except dynamodb.exceptions.ResourceInUseException:
        print(f"✓ DynamoDB table already exists: {DYNAMODB_TABLE_NAME}")
    except Exception as e:
        print(f"✗ Error creating DynamoDB table: {e}")


def create_lambda_role():
    """Create IAM role for Lambda function"""
    print(f"Creating IAM role for Lambda: {LAMBDA_ROLE_NAME}...")
    
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    
    try:
        iam.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description='Role for Automotive Lambda function'
        )
        
        # Attach basic execution policy
        iam.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        print(f"✓ IAM role created: {LAMBDA_ROLE_NAME}")
        time.sleep(10)  # Wait for role to propagate
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"✓ IAM role already exists: {LAMBDA_ROLE_NAME}")
    except Exception as e:
        print(f"✗ Error creating IAM role: {e}")
    
    return f'arn:aws:iam::{ACCOUNT_ID}:role/{LAMBDA_ROLE_NAME}'


def create_lambda_function():
    """Create Lambda function for price analysis"""
    print(f"Creating Lambda function: {LAMBDA_FUNCTION_NAME}...")
    
    # Lambda function code
    lambda_code = '''
import json
from datetime import datetime

def lambda_handler(event, context):
    """Analyze vehicle price based on make, model, year"""
    
    # Depreciation rates
    DEPRECIATION_RATES = {1: 0.20, 2: 0.15, 3: 0.12, 4: 0.10, 5: 0.08}
    
    # Make factors
    MAKE_FACTORS = {
        'toyota': 1.10, 'honda': 1.08, 'ford': 1.00,
        'chevrolet': 0.98, 'bmw': 1.15, 'mercedes': 1.20,
        'audi': 1.12, 'tesla': 1.25
    }
    
    try:
        make = event.get('make', '').lower()
        year = int(event.get('year', datetime.now().year))
        price = float(event.get('price', 30000))
        
        # Calculate age
        age = datetime.now().year - year
        
        # Calculate depreciation
        value = price
        for y in range(1, age + 1):
            rate = DEPRECIATION_RATES.get(y, 0.08)
            value *= (1 - rate)
        
        # Apply make factor
        make_factor = MAKE_FACTORS.get(make, 1.0)
        adjusted_value = value * make_factor
        
        return {
            'statusCode': 200,
            'body': {
                'original_price': price,
                'current_value': round(adjusted_value, 2),
                'depreciation': round(price - adjusted_value, 2),
                'depreciation_percent': round((price - adjusted_value) / price * 100, 1),
                'age': age,
                'make_factor': make_factor
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }
'''
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('lambda_function.py', lambda_code)
    zip_buffer.seek(0)
    
    role_arn = create_lambda_role()
    
    try:
        lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime='python3.11',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_buffer.read()},
            Description='Vehicle price analyzer for Automotive app',
            Timeout=30,
            MemorySize=128
        )
        print(f"✓ Lambda function created: {LAMBDA_FUNCTION_NAME}")
    except lambda_client.exceptions.ResourceConflictException:
        print(f"✓ Lambda function already exists: {LAMBDA_FUNCTION_NAME}")
    except Exception as e:
        print(f"✗ Error creating Lambda function: {e}")


def create_cloudwatch_log_group():
    """Create CloudWatch log group"""
    print(f"Creating CloudWatch log group: {CLOUDWATCH_LOG_GROUP}...")
    try:
        logs.create_log_group(logGroupName=CLOUDWATCH_LOG_GROUP)
        
        # Set retention to 7 days
        logs.put_retention_policy(
            logGroupName=CLOUDWATCH_LOG_GROUP,
            retentionInDays=7
        )
        
        print(f"✓ CloudWatch log group created: {CLOUDWATCH_LOG_GROUP}")
    except logs.exceptions.ResourceAlreadyExistsException:
        print(f"✓ CloudWatch log group already exists: {CLOUDWATCH_LOG_GROUP}")
    except Exception as e:
        print(f"✗ Error creating CloudWatch log group: {e}")


def create_ssm_parameters():
    """Create SSM parameters for secrets"""
    print("Creating SSM parameters...")
    
    parameters = [
        ('/automotive/flask-secret-key', 'automotive-secret-key-2024', 'SecureString'),
        ('/automotive/app-name', 'AutoMotive Hub', 'String'),
        ('/automotive/environment', 'production', 'String')
    ]
    
    for name, value, param_type in parameters:
        try:
            ssm.put_parameter(
                Name=name,
                Value=value,
                Type=param_type,
                Overwrite=True
            )
            print(f"✓ SSM parameter created: {name}")
        except Exception as e:
            print(f"✗ Error creating SSM parameter {name}: {e}")


def main():
    """Main function to create all AWS resources"""
    print("=" * 60)
    print("AWS Infrastructure Setup for Automotive Flask App")
    print("=" * 60)
    print(f"Region: {AWS_REGION}")
    print(f"Account: {ACCOUNT_ID}")
    print("=" * 60)
    
    create_s3_bucket()
    create_dynamodb_table()
    create_lambda_function()
    create_cloudwatch_log_group()
    create_ssm_parameters()
    
    print("=" * 60)
    print("Infrastructure setup complete!")
    print("=" * 60)
    print("\nCreated Resources:")
    print(f"  - S3 Bucket: {S3_BUCKET_NAME}")
    print(f"  - DynamoDB Table: {DYNAMODB_TABLE_NAME}")
    print(f"  - Lambda Function: {LAMBDA_FUNCTION_NAME}")
    print(f"  - CloudWatch Log Group: {CLOUDWATCH_LOG_GROUP}")
    print(f"  - SSM Parameters: /automotive/*")


if __name__ == '__main__':
    main()
