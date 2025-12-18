from flask import (
    Blueprint, current_app, request, flash,
    redirect, url_for, render_template
)

import pulumi
import pulumi_aws as aws
import pulumi.automation as auto
import os
from pathlib import Path

bp = Blueprint("virtual_machines", __name__, url_prefix="/vms")
instance_types = ['c5.xlarge', 'p2.xlarge', 'p3.2xlarge']


def create_pulumi_program(keydata: str, instance_type: str):

    # --- AMI ---
    ami = aws.ec2.get_ami(
        most_recent=True,
        owners=["amazon"],
        filters=[{
            "name": "name",
            "values": ["amzn2-ami-hvm-*-x86_64-gp2"]
        }]
    )

    # --- VPC ---
    vpc = aws.ec2.Vpc(
        "vm-vpc",
        cidr_block="10.0.0.0/16",
        enable_dns_support=True,
        enable_dns_hostnames=True,
    )

    # --- Internet Gateway ---
    igw = aws.ec2.InternetGateway(
        "vm-igw",
        vpc_id=vpc.id,
    )

    # --- Route Table ---
    route_table = aws.ec2.RouteTable(
        "vm-rt",
        vpc_id=vpc.id,
        routes=[
            aws.ec2.RouteTableRouteArgs(
                cidr_block="0.0.0.0/0",
                gateway_id=igw.id,
            )
        ],
    )

    # --- Subnet ---
    subnet = aws.ec2.Subnet(
        "vm-subnet",
        vpc_id=vpc.id,
        cidr_block="10.0.1.0/24",
        availability_zone="us-east-1a",
    )

    aws.ec2.RouteTableAssociation(
        "vm-rta",
        subnet_id=subnet.id,
        route_table_id=route_table.id,
    )

    # --- Security Group ---
    group = aws.ec2.SecurityGroup(
        "web-secgrp",
        vpc_id=vpc.id,
        description="Enable SSH access",
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=22,
                to_port=22,
                cidr_blocks=["0.0.0.0/0"],
            )
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                protocol="-1",
                from_port=0,
                to_port=0,
                cidr_blocks=["0.0.0.0/0"],
            )
        ],
    )

    # --- SSH Key ---
    public_key = keydata
    if not public_key:
        home = str(Path.home())
        with open(os.path.join(home, ".ssh/id_rsa.pub")) as f:
            public_key = f.read()

    public_key = public_key.strip()

    keypair = aws.ec2.KeyPair(
        "dlami-keypair",
        public_key=public_key,
    )

    # --- EC2 Instance ---
    server = aws.ec2.Instance(
        "dlami-server",
        ami=ami.id,
        instance_type=instance_type,
        subnet_id=subnet.id,                       # REQUIRED
        vpc_security_group_ids=[group.id],         # MUST be IDs
        associate_public_ip_address=True,          # REQUIRED
        key_name=keypair.key_name,                 # FIXED
    )

    pulumi.export("instance_type", server.instance_type)
    pulumi.export("public_key", keypair.public_key)
    pulumi.export("public_ip", server.public_ip)
    pulumi.export("public_dns", server.public_dns)

@bp.route("/new", methods=["GET", "POST"])
def create_vm():
    """creates new VM"""
    if request.method == "POST":
        stack_name = request.form.get("vm-id")
        keydata = request.form.get("vm-keypair")
        instance_type = request.form.get("instance_type")

        def pulumi_program():
            return create_pulumi_program(keydata, instance_type)
        try:
            # create a new stack, generating our pulumi program on the fly from the POST body
            stack = auto.create_stack(
                stack_name=str(stack_name),
                project_name=current_app.config["PROJECT_NAME"],
                program=pulumi_program,
            )
            stack.set_config("aws:region", auto.ConfigValue("us-east-1"))
            # deploy the stack, tailing the logs to stdout
            stack.up(on_output=print)
            flash(
                f"Successfully created VM '{stack_name}'", category="success")
        except auto.StackAlreadyExistsError:
            flash(
                f"Error: VM with name '{stack_name}' already exists, pick a unique name",
                category="danger",
            )
        return redirect(url_for("virtual_machines.list_vms"))

    current_app.logger.info(f"Instance types: {instance_types}")
    return render_template("virtual_machines/create.html", instance_types=instance_types, curr_instance_type=None)


@bp.route("/", methods=["GET"])
def list_vms():
    """lists all vms"""
    vms = []
    org_name = current_app.config["PULUMI_ORG"]
    project_name = current_app.config["PROJECT_NAME"]
    try:
        ws = auto.LocalWorkspace(
            project_settings=auto.ProjectSettings(
                name=project_name, runtime="python")
        )
        all_stacks = ws.list_stacks()
        for stack in all_stacks:
            stack = auto.select_stack(
                stack_name=stack.name,
                project_name=project_name,
                # no-op program, just to get outputs
                program=lambda: None,
            )
            outs = stack.outputs()
            if 'public_dns' in outs:
                vms.append(
                    {
                        "name": stack.name,
                        "dns_name": f"{outs['public_dns'].value}",
                        "console_url": f"https://app.pulumi.com/{org_name}/{project_name}/{stack.name}",
                    }
                )
    except Exception as exn:
        flash(str(exn), category="danger")

    current_app.logger.info(f"VMS: {vms}")
    return render_template("virtual_machines/index.html", vms=vms)


@bp.route("/<string:id>/update", methods=["GET", "POST"])
def update_vm(id: str):
    stack_name = id
    if request.method == "POST":
        current_app.logger.info(
            f"Updating VM: {stack_name}, form data: {request.form}")
        keydata = request.form.get("vm-keypair")
        current_app.logger.info(f"updating keydata: {keydata}")
        instance_type = request.form.get("instance_type")

        def pulumi_program():
            return create_pulumi_program(keydata, instance_type)
        try:
            stack = auto.select_stack(
                stack_name=stack_name,
                project_name=current_app.config["PROJECT_NAME"],
                program=pulumi_program,
            )
            stack.set_config("aws:region", auto.ConfigValue("us-east-1"))
            # deploy the stack, tailing the logs to stdout
            stack.up(on_output=print)
            flash(f"VM '{stack_name}' successfully updated!",
                  category="success")
        except auto.ConcurrentUpdateError:
            flash(
                f"Error: VM '{stack_name}' already has an update in progress",
                category="danger",
            )
        except Exception as exn:
            flash(str(exn), category="danger")
        return redirect(url_for("virtual_machines.list_vms"))

    stack = auto.select_stack(
        stack_name=stack_name,
        project_name=current_app.config["PROJECT_NAME"],
        # noop just to get the outputs
        program=lambda: None,
    )
    outs = stack.outputs()
    public_key = outs.get("public_key")
    pk = public_key.value if public_key else None
    instance_type = outs.get("instance_type")
    return render_template("virtual_machines/update.html", name=stack_name, public_key=pk, instance_types=instance_types, curr_instance_type=instance_type.value)


@bp.route("/<string:id>/delete", methods=["POST"])
def delete_vm(id: str):
    stack_name = id
    try:
        stack = auto.select_stack(
            stack_name=stack_name,
            project_name=current_app.config["PROJECT_NAME"],
            # noop program for destroy
            program=lambda: None,
        )
        stack.destroy(on_output=print)
        stack.workspace.remove_stack(stack_name)
        flash(f"VM '{stack_name}' successfully deleted!", category="success")
    except auto.ConcurrentUpdateError:
        flash(
            f"Error: VM '{stack_name}' already has update in progress",
            category="danger",
        )
    except Exception as exn:
        flash(str(exn), category="danger")

    return redirect(url_for("virtual_machines.list_vms"))