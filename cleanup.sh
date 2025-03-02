#!/bin/bash

echo "Starting cleanup..."

# Get the latest running instance ID
INSTANCE_ID=$(aws ec2 describe-instances \
    --filters \
        "Name=tag:Name,Values=video-processor" \
        "Name=instance-state-name,Values=running,pending,stopping,stopped" \
    --query 'sort_by(Reservations[].Instances[], &LaunchTime)[-1].InstanceId' \
    --output text)

if [ ! -z "$INSTANCE_ID" ] && [ "$INSTANCE_ID" != "None" ]; then
    echo "Found instance: $INSTANCE_ID"

    # Terminate the instance
    echo "Terminating instance..."
    aws ec2 terminate-instances --instance-ids $INSTANCE_ID

    # Wait for instance to terminate
    echo "Waiting for instance to terminate..."
    aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID
    echo "Instance terminated successfully"
else
    echo "No running instances found"
fi

# Find all security groups with name video-processor-sg
echo "Finding security groups..."
SG_IDS=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=video-processor-sg" \
    --query 'SecurityGroups[*].GroupId' \
    --output text)

if [ ! -z "$SG_IDS" ]; then
    echo "Found security groups: $SG_IDS"

    # Delete each security group
    for SG_ID in $SG_IDS; do
        echo "Attempting to delete security group: $SG_ID"

        # Try to delete the security group multiple times
        MAX_ATTEMPTS=5
        ATTEMPT=1

        while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
            if aws ec2 delete-security-group --group-id $SG_ID 2>/dev/null; then
                echo "Successfully deleted security group: $SG_ID"
                break
            else
                echo "Attempt $ATTEMPT: Failed to delete security group. Waiting before retry..."
                sleep 10
                ATTEMPT=$((ATTEMPT + 1))
            fi
        done

        if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
            echo "Failed to delete security group $SG_ID after $MAX_ATTEMPTS attempts"
        fi
    done
else
    echo "No security groups found"
fi

echo "Cleanup completed!"

# Print current state
echo -e "\nCurrent State:"
echo "Checking for any remaining instances..."
aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=video-processor" \
    --query 'Reservations[].Instances[].[InstanceId,State.Name]' \
    --output table

echo "Checking for any remaining security groups..."
aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=video-processor-sg" \
    --query 'SecurityGroups[].[GroupId,GroupName]' \
    --output table