""" PTL-TEST-RDS-JENKINS-L """
import datetime
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)
print('Loading function')

def delete_rds_instance(rds_db_identifier, skip_final_snap=True, final_snap_name='NA'):
    """
    Delete RDS Instance
    Argments:
    rds_db_identifier -- RDS DB Name Indentifier (String - Required - No Default)
    skip_final_snap --- Skip Final Snapshot on Delete (Boolean - Optional - Default: True)
    final_snap_name --- Final Snapshot Name \
        String - Optional / Required if skip_final_snap = False - Default: 'NA')
    """
    print('Function Called: delete_rds_instance')
    print('Arguments: %s, %s, %s' % (rds_db_identifier, skip_final_snap, final_snap_name))
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
    print('delete_rds_instance response: %s' % delete_rds)
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
    print('Arguments: %s, %s, %s' % (rds_db_identifier, rds_snap, rds_subnet))
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
    print('create_rds_from_snapshot response: %s' % create_rds)
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
    print('Arguments: %s, %s, %s' % (rds_db_identifier, rds_sgid, rds_params))
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
    print('modify_rds_instance response: %s' % modify_rds)
    return

def get_vpc_sgid(sg_name):
    """
    Retrieve Security Group ID for a given SG Name
    Argments:
    sg_name -- VPC Security Group Name for which to retrieve SGID (String - Required - No Default)
    """
    print('Function Called: get_vpc_sgid')
    print('Arguments: %s' % sg_name)
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
    print('sg_response = %s' % sg_response)
    sgid = sg_response['SecurityGroups'][0]['GroupId']
    return sgid

def get_rds_status(rds_name):
    """
    Get Status of a Given RDS Instance
    Argments:
    rds_name -- Name of RDS Instance to Fetch Status Of (String - Required - No Default)
    """
    print('Function Called: get_rds_status')
    print('Arguments: %s' % rds_name)
    rds = boto3.client('rds')
    response = rds.describe_db_instances(
        DBInstanceIdentifier=rds_name \
    )
    print('get_rds_status response: %s' % response)
    return response['DBInstances'][0]['DBInstanceStatus']

def reboot_rds_instance(rds_name):
    """
    Reboot a Given RDS Instance
    Argments:
    rds_name -- Name of RDS Instance to Reboot (String - Required - No Default)
    """
    print('Function Called: reboot_rds_instance')
    print('Arguments: %s' % rds_name)
    rds = boto3.client('rds')
    response = rds.reboot_db_instance(
        DBInstanceIdentifier=rds_name \
    )
    print('reboot_rds_instance response: %s' % response)
    return response['DBInstance']['DBInstanceStatus']

def rds_instance_exists(rds_name):
    """
    Check a given RDS instance exists - returns boolean
    Argments:
    rds_name -- Name of RDS Instance to validate (String - Required - No Default)
    """
    print('Function Called: rds_instance_exists')
    print('Arguments: %s' % rds_name)
    exists = False
    try:
        rds = boto3.client('rds')
        response = rds.describe_db_instances(
            DBInstanceIdentifier=rds_name \
        )
        print('rds_instance_exists response: %s' % response)
        return True
    except ClientError as err:
        print('ClientError: %s' % err)
        if err.response['Error']['Code'] == "DBInstanceNotFound":
            print('DBInstanceNotFound for: %s' % rds_name)
        else:
            print("Boto Client Error: %s" % err)
        return False
    except Exception as xerror:
        print("rds_instance_exists - Unexpected error: %s" % xerror)
        return False

# Main Handler
def lambda_handler(event, context):
    """ Entry Function """
    # Test Event: {
    #  "EventType": "RestoreRDSInstanceFromSnapshot",
    #  "RDSName": "devappps-ptl-test-rds",
    #  "RDSBaseSnap": "devappps-ptl-test-rds-basesnap001",
    #  "RDSSubnet": "devappps-olcs-rds-devapppsew",
    #  "RDSSG": "DEV/APP/PS-OLCS-RDS-ADDRESS-SG",
    #  "RDSParamGroup": "triggersenabled57" }
    print('Function Called: lambda_handler')
    print('Event Message: %s' % event)
    if event['EventType'] == "TerminateRDSInstance":
        print('Terminate RDS Instance Event Recieved')
        rds_name = event['RDSName']
        is_valid = rds_instance_exists(rds_name)
        if is_valid:
            print('RDS To Terminate: %s' % rds_name)
            # Build timestamped name for final snapshot
            now = datetime.datetime.now()
            snap_time = now.strftime('%d') + '-' \
                + now.strftime('%m') + '-' \
                + now.strftime('%y') + '-' \
                + now.strftime('%H') \
                + now.strftime('%M') \
                + now.strftime('%S')
            final_snap_name = rds_name + '-' + snap_time
            # TODO - check current status of rds instance - only delete if running
            try:
                delete_rds_instance(rds_name, False, final_snap_name)
                # TODO validate response - return delete_rds from the function and check for
                # 'DBInstanceStatus': 'deleting'
                return 'TerminateComplete'
            except Exception as xerror:
                print("Terminate RDS - Unexpected error: %s" % xerror)
                return xerror
        else:
            return 'RDS Instance Does Not Exist'
    elif event['EventType'] == "RestoreRDSInstanceFromSnapshot":
        print('Restore RDS Instance From Snapshot Event Received')
        rds_name = event['RDSName']
        rds_base_snap = event['RDSBaseSnap']
        rds_subnet = event['RDSSubnet']
        is_valid = rds_instance_exists(rds_name)
        if not is_valid:
            try:
                create_rds_from_snapshot(rds_name, rds_base_snap, rds_subnet)
                return 'RestoreDBComplete'
            except Exception as xerror:
                print("RestoreDBFromSnapshot - Unexpected error: %s" % xerror)
                return xerror
        else:
            return 'RDSInstanceAlreadyExists'
    elif event['EventType'] == "ModifyRestoredDB":
        rds_name = event['RDSName']
        rds_sg = event['RDSSG']
        rds_params = event['RDSParamGroup']
        is_valid = rds_instance_exists(rds_name)
        if is_valid:
            try:
                # Get SG ID
                rds_sgid = get_vpc_sgid(rds_sg)
                modify_rds_instance(rds_name, rds_sgid, rds_params)
                return 'LaunchComplete'
            except Exception as xerror:
                print("ModifyRestoredDB - Unexpected error: %s" % xerror)
                return xerror
        else:
            return 'RDSInstanceDoesNotExist'
    elif event['EventType'] == "GetRDSStatus":
        rds_name = event['RDSName']
        is_valid = rds_instance_exists(rds_name)
        if is_valid:
            print("RDS Instance Valid Check: %s" % is_valid)
            try:
                rds_status = get_rds_status(rds_name)
                return rds_status
            except Exception as xerror:
                print("GetRDSStatus - Unexpected error: %s" % xerror)
                return xerror
        else:
            return 'RDSInstanceDoesNotExist'
    elif event['EventType'] == "RebootRDSInstance":
        rds_name = event['RDSName']
        is_valid = rds_instance_exists(rds_name)
        if is_valid:
            try:
                rds_reboot = reboot_rds_instance(rds_name)
                return rds_reboot
            except Exception as xerror:
                print("RebootRDSInstance - Unexpected error: %s" % xerror)
                return xerror
        else:
            return 'RDSInstanceDoesNotExist'
    else:
        print('Invalid EventType Received')
        return 'Invalid Event Type'
