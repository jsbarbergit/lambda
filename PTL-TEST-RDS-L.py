""" PTL-TEST-RDS-L """
import datetime
import logging
import json
import boto3
logger = logging.getLogger()
logger.setLevel(logging.INFO)
print('Loading function')


# Get ASG Tags
def get_asg_tags(asg_name):
    """
	Retrieve ASG Tags Function
	Argments:
	asg_name -- Auto Scaling Group Name (String - Required - No Default)
	"""
    print('Function Called: get_asg_tags')
    print('Argument: %s', asg_name)
    asg = boto3.client('autoscaling')
    # Get the ASG Tags
    response = asg.describe_tags(
        Filters=[ \
            { \
                'Name': 'auto-scaling-group', \
                'Values': [ \
                    asg_name \
                ] \
            } \
        ] \
    )
    return response

# Delete RDS DB Instance - take final snapshot
def delete_rds_instance(rds_db_identifier, skip_final_snap=True, final_snap_name='NA'):
    """
	Delete RDS Instance
	Argments:
	rds_db_identifier -- RDS DB Name Indentifier (String - Required - No Default)
	skip_final_snap --- Skip Final Snapshot on Delete (Boolean - Optional - Default: True)
	final_snap_name --- Final Snapshot Name \
		(String - Optional / Required if skip_final_snap = False - Default: 'NA')
	"""
    print('Function Called: delete_rds_instance')
    print('Arguments: %s, %s, %s', rds_db_identifier, skip_final_snap, final_snap_name)
	# Delete running RDS instance + take final snap
    rds = boto3.client('rds')
    if skip_final_snap:
        delete_rds = rds.delete_db_instance(
            DBInstanceIdentifier=rds_db_identifier,
            SkipFinalSnapshot=skip_final_snap
        )
    else:
        delete_rds = rds.delete_db_instance(
            DBInstanceIdentifier=rds_db_identifier,
            SkipFinalSnapshot=skip_final_snap,
            FinalDBSnapshotIdentifier=final_snap_name
        )
    print(delete_rds)
    return

def create_rds_from_snapshot(rds_db_identifier, rds_snap, rds_subnet):
    """
    Create RDS Instance from snapshot
    Argments:
    rds_db_identifier -- RDS DB Name Indentifier (String - Required - No Default)
    rds_snap --- RDS Snapshot to Restore from (String - Required - No Default)
	rds_subnet --- RDS Subnet Group Name (String - Required - No Default)
    """
    print('Function Called: create_rds_from_snapshot')
    print('Arguments: %s, %s, %s', rds_db_identifier, rds_snap, rds_subnet)
    # TODO Validate snapshot exists
    # TODO Validate RDS instance of given name does not already exist
    # Create RDS Instance from given snapshot
	# Restored RDS instance will inherit snapshot properties - except Parameter and SG group values
    rds = boto3.client('rds')
    create_rds = rds.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier=rds_db_identifier, \
        DBSnapshotIdentifier=rds_snap, \
        DBSubnetGroupName=rds_subnet \
    )
    print(create_rds)
    return

def modify_rds_instance(rds_db_identifier, rds_sgid, rds_params):
    """
    Modify RDS Instance Security and Parameter Groups following restore from snapshot
    Argments:
    rds_db_identifier -- RDS DB Name Indentifier (String - Required - No Default)
    rds_sg --- Security Group to assign RDS Instance to (String - Required - No Default)
    rds_params --- RDS Parameter Group to switch to (String - Required - No Default)
    """
    print('Function Called: modify_rds_instance')
    print('Arguments: %s, %s, %s', rds_db_identifier, rds_sgid, rds_params)
    # TODO Validate DB exists
    # TODO Validate SG exists
    # TODO Validate Param Group exists
    rds = boto3.client('rds')
    modify_rds = rds.modify_db_instance(
        DBInstanceIdentifier=rds_db_identifier, \
        VpcSecurityGroupIds=[ \
            rds_sgid \
        ],
        DBParameterGroupName=rds_params,
        ApplyImmediately=True
    )
    print(modify_rds)
    return

def get_vpc_sgid(sg_name):
    """
    Retrieve Security Group ID for a given SG Name
    Argments:
    sg_name -- VPC Security Group Name for which to retrieve SGID
    """
    print('Function Called: get_vpc_sgid')
    print('Arguments: %s', sg_name)
    ec2 = boto3.client('ec2')
    sg_response = ec2.describe_security_groups(
        Filters=[ \
            { \
                'Name': 'group-name',
                'Values': [ \
                    sg_name, \
                ] \
            } \
        ] \
    )
    print('sg_response = %s', sg_response)
    sgid = sg_response['SecurityGroups'][0]['GroupId']
    return sgid

# Main Handler
def lambda_handler(event, context):
    """ Entry Function """
    logger.info('PTL-TEST-RDS-L event{}'.format(event))
    message = json.loads(event['Records'][0]['Sns']['Message'])
    print('Event Message: ' + message['Event'])
    if message['Event'] == "autoscaling:EC2_INSTANCE_TERMINATE":
        print('ASG Terminate Instance Event Recieved')
        asg_name = message['AutoScalingGroupName']
        response = get_asg_tags(asg_name)
        for item in response['Tags']:
            if item['Key'] == 'PTLRDS':
                print('RDS To Terminate: ' + item['Value'])
                # Build timestamped name for final snapshot
                now = datetime.datetime.now()
                snap_time = now.strftime('%d') + '-' \
					+ now.strftime('%m') + '-' \
					+ now.strftime('%y') + '-' \
					+ now.strftime('%H') \
					+ now.strftime('%M') \
					+ now.strftime('%S')
                final_snap_name = item['Value'] + '-' + snap_time
                # TODO - check current status of rds instance - only delete if running
                try:
                    delete_rds_instance(item['Value'], False, final_snap_name)
					# TODO validate response - return delete_rds from the function and check for
					# 'DBInstanceStatus': 'deleting'
                except Exception as xerror:
                    print("Unexpected error: %s", xerror)
                    return 'Terminate Failed'
                return 'Terminate Complete'
    elif message['Event'] == "autoscaling:EC2_INSTANCE_LAUNCH":
        print('ASG Launch Event Received')
        # Get ASG Name
        print('ASG Terminate Instance Event Recieved')
        asg_name = message['AutoScalingGroupName']
        response = get_asg_tags(asg_name)
        for item in response['Tags']:
            if item['Key'] == 'PTLRDS':
                rds_name = item['Value']
            if item['Key'] == 'PTLRDSSNAP':
                rds_base_snap = item['Value']
            if item['Key'] == 'PTLRDSSUBNET':
                rds_subnet = item['Value']
            if item['Key'] == 'PTLRDSSG':
                rds_sg = item['Value']
            if item['Key'] == 'PTLRDSPARAMS':
                rds_params = item['Value']
        try:
            create_rds_from_snapshot(rds_name, rds_base_snap, rds_subnet)
			# Get SG ID
            rds_sgid = get_vpc_sgid(rds_sg)
            modify_rds_instance(rds_name, rds_sgid, rds_params)
        except Exception as xerror:
            print("Unexpected error: %s", xerror)
            return 'Launch Failed'
        return 'Launch Complete'
    else:
        print('Incompatible event received')
    return
	