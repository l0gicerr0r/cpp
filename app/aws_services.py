"""
AWS Services Integration Module
Services: S3 (Object Storage), DynamoDB (Database), Lambda (Serverless), 
          CloudWatch (Logging), SSM Parameter Store (Secrets)
"""

import boto3
import json
import logging
from datetime import datetime
from botocore.exceptions import ClientError

# AWS Configuration
AWS_REGION = 'eu-west-1'
S3_BUCKET_NAME = 'automotive-app-images-565209206796'
DYNAMODB_TABLE_NAME = 'automotive-activity-logs'
LAMBDA_FUNCTION_NAME = 'automotive-price-analyzer'
CLOUDWATCH_LOG_GROUP = '/automotive-app/logs'

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
lambda_client = boto3.client('lambda', region_name=AWS_REGION)
cloudwatch_logs = boto3.client('logs', region_name=AWS_REGION)
ssm_client = boto3.client('ssm', region_name=AWS_REGION)


class S3Service:
    """AWS S3 Service for object storage"""
    
    def __init__(self, bucket_name=S3_BUCKET_NAME):
        self.bucket_name = bucket_name
        self.client = s3_client
    
    def upload_file(self, file_obj, filename, content_type='image/jpeg'):
        """Upload a file to S3"""
        try:
            key = f"vehicles/{datetime.utcnow().strftime('%Y%m%d')}/{filename}"
            self.client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs={'ContentType': content_type}
            )
            url = f"https://{self.bucket_name}.s3.{AWS_REGION}.amazonaws.com/{key}"
            return {'success': True, 'url': url, 'key': key}
        except ClientError as e:
            logging.error(f"S3 upload error: {e}")
            return {'success': False, 'error': str(e)}
    
    def delete_file(self, key):
        """Delete a file from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return {'success': True}
        except ClientError as e:
            logging.error(f"S3 delete error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_presigned_url(self, key, expiration=3600):
        """Generate a presigned URL for secure access"""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return {'success': True, 'url': url}
        except ClientError as e:
            return {'success': False, 'error': str(e)}


class DynamoDBService:
    """AWS DynamoDB Service for activity logging"""
    
    def __init__(self, table_name=DYNAMODB_TABLE_NAME):
        self.table_name = table_name
        self.table = dynamodb.Table(table_name)
    
    def log_activity(self, user_id, action, details=None):
        """Log user activity"""
        try:
            item = {
                'activity_id': f"{user_id}_{datetime.utcnow().timestamp()}",
                'user_id': str(user_id),
                'action': action,
                'details': details or {},
                'timestamp': datetime.utcnow().isoformat(),
                'date': datetime.utcnow().strftime('%Y-%m-%d')
            }
            self.table.put_item(Item=item)
            return {'success': True, 'activity_id': item['activity_id']}
        except ClientError as e:
            logging.error(f"DynamoDB error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_activities(self, user_id, limit=10):
        """Get recent activities for a user"""
        try:
            response = self.table.query(
                IndexName='user-index',
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': str(user_id)},
                Limit=limit,
                ScanIndexForward=False
            )
            return {'success': True, 'activities': response.get('Items', [])}
        except ClientError as e:
            logging.error(f"DynamoDB query error: {e}")
            return {'success': False, 'error': str(e), 'activities': []}


class LambdaService:
    """AWS Lambda Service for serverless computing"""
    
    def __init__(self, function_name=LAMBDA_FUNCTION_NAME):
        self.function_name = function_name
        self.client = lambda_client
    
    def invoke_price_analysis(self, vehicle_data):
        """Invoke Lambda function for price analysis"""
        try:
            payload = json.dumps(vehicle_data)
            response = self.client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',
                Payload=payload
            )
            result = json.loads(response['Payload'].read().decode('utf-8'))
            return {'success': True, 'result': result}
        except ClientError as e:
            logging.error(f"Lambda invoke error: {e}")
            return {'success': False, 'error': str(e)}


class CloudWatchService:
    """AWS CloudWatch Service for logging"""
    
    def __init__(self, log_group=CLOUDWATCH_LOG_GROUP):
        self.log_group = log_group
        self.client = cloudwatch_logs
        self.log_stream = f"app-{datetime.utcnow().strftime('%Y-%m-%d')}"
    
    def log_event(self, message, level='INFO'):
        """Log an event to CloudWatch"""
        try:
            # Ensure log stream exists
            try:
                self.client.create_log_stream(
                    logGroupName=self.log_group,
                    logStreamName=self.log_stream
                )
            except self.client.exceptions.ResourceAlreadyExistsException:
                pass
            
            log_message = f"[{level}] {datetime.utcnow().isoformat()} - {message}"
            self.client.put_log_events(
                logGroupName=self.log_group,
                logStreamName=self.log_stream,
                logEvents=[{
                    'timestamp': int(datetime.utcnow().timestamp() * 1000),
                    'message': log_message
                }]
            )
            return {'success': True}
        except ClientError as e:
            logging.error(f"CloudWatch error: {e}")
            return {'success': False, 'error': str(e)}


class SSMService:
    """AWS SSM Parameter Store for secrets management"""
    
    def __init__(self):
        self.client = ssm_client
    
    def get_parameter(self, name, decrypt=True):
        """Get a parameter from SSM"""
        try:
            response = self.client.get_parameter(
                Name=name,
                WithDecryption=decrypt
            )
            return {'success': True, 'value': response['Parameter']['Value']}
        except ClientError as e:
            logging.error(f"SSM get error: {e}")
            return {'success': False, 'error': str(e)}
    
    def put_parameter(self, name, value, param_type='SecureString'):
        """Store a parameter in SSM"""
        try:
            self.client.put_parameter(
                Name=name,
                Value=value,
                Type=param_type,
                Overwrite=True
            )
            return {'success': True}
        except ClientError as e:
            logging.error(f"SSM put error: {e}")
            return {'success': False, 'error': str(e)}


# Initialize service instances
s3_service = S3Service()
dynamodb_service = DynamoDBService()
lambda_service = LambdaService()
cloudwatch_service = CloudWatchService()
ssm_service = SSMService()
