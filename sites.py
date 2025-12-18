import json
import requests
from flask import (
    current_app,
    Blueprint,
    request,
    flash,
    redirect,
    url_for,
    render_template,
)

import pulumi
import pulumi.automation as auto
from pulumi_aws import s3

bp = Blueprint("sites", __name__, url_prefix="/sites")


def create_pulumi_program(content: str):
    # 1. Public S3 bucket with website hosting
    site_bucket = s3.Bucket(
        "s3-website-bucket",
        website=s3.BucketWebsiteArgs(
            index_document="index.html"
        ),
    )

    # 2. Upload index.html
    s3.BucketObject(
        "index",
        bucket=site_bucket.id,
        content=content,
        key="index.html",
        content_type="text/html; charset=utf-8",
    )

    # 3. Public bucket policy (ALLOW GET)
    s3.BucketPolicy(
    "bucket-policy",
    bucket=site_bucket.id,
    policy=site_bucket.id.apply(
        lambda bucket_name: json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        })
    )
)

    # 4. Outputs
    pulumi.export("website_url", site_bucket.website_endpoint)
    pulumi.export("website_content", content)


@bp.route("/new", methods=["GET", "POST"])
def create_site():
    if request.method == "POST":
        stack_name = request.form.get("site-id")
        file_url = request.form.get("file-url")

        if file_url:
            site_content = requests.get(file_url).text
        else:
            site_content = request.form.get("site-content")

        def pulumi_program():
            create_pulumi_program(str(site_content))

        try:
            stack = auto.create_stack(
                stack_name=str(stack_name),
                project_name=current_app.config["PROJECT_NAME"],
                program=pulumi_program,
            )
            stack.set_config("aws:region", auto.ConfigValue("us-east-1"))
            stack.up(on_output=print)

            flash(f"Successfully created site '{stack_name}'", category="success")
        except auto.StackAlreadyExistsError:
            flash(
                f"Error: Site with name '{stack_name}' already exists",
                category="danger",
            )

        return redirect(url_for("sites.list_sites"))

    return render_template("sites/create.html")


@bp.route("/", methods=["GET"])
def list_sites():
    sites = []
    org_name = current_app.config["PULUMI_ORG"]
    project_name = current_app.config["PROJECT_NAME"]

    try:
        ws = auto.LocalWorkspace(
            project_settings=auto.ProjectSettings(
                name=project_name, runtime="python"
            )
        )
        for stack_info in ws.list_stacks():
            stack = auto.select_stack(
                stack_name=stack_info.name,
                project_name=project_name,
                program=lambda: None,
            )
            outs = stack.outputs()
            if "website_url" in outs:
                sites.append(
                    {
                        "name": stack_info.name,
                        "url": f"http://{outs['website_url'].value}",
                        "console_url": f"https://app.pulumi.com/{org_name}/{project_name}/{stack_info.name}",
                    }
                )
    except Exception as exn:
        flash(str(exn), category="danger")

    return render_template("sites/index.html", sites=sites)


@bp.route("/<string:id>/update", methods=["GET", "POST"])
def update_site(id: str):
    if request.method == "POST":
        file_url = request.form.get("file-url")
        if file_url:
            site_content = requests.get(file_url).text
        else:
            site_content = request.form.get("site-content")

        def pulumi_program():
            create_pulumi_program(str(site_content))

        try:
            stack = auto.select_stack(
                stack_name=id,
                project_name=current_app.config["PROJECT_NAME"],
                program=pulumi_program,
            )
            stack.set_config("aws:region", auto.ConfigValue("us-east-1"))
            stack.up(on_output=print)

            flash(f"Site '{id}' successfully updated!", category="success")
        except Exception as exn:
            flash(str(exn), category="danger")

        return redirect(url_for("sites.list_sites"))

    stack = auto.select_stack(
        stack_name=id,
        project_name=current_app.config["PROJECT_NAME"],
        program=lambda: None,
    )
    outs = stack.outputs()
    content = outs.get("website_content").value if "website_content" in outs else ""
    return render_template("sites/update.html", name=id, content=content)


@bp.route("/<string:id>/delete", methods=["POST"])
def delete_site(id: str):
    try:
        stack = auto.select_stack(
            stack_name=id,
            project_name=current_app.config["PROJECT_NAME"],
            program=lambda: None,
        )
        stack.destroy(on_output=print)
        stack.workspace.remove_stack(id)
        flash(f"Site '{id}' successfully deleted!", category="success")
    except Exception as exn:
        flash(str(exn), category="danger")

    return redirect(url_for("sites.list_sites"))
