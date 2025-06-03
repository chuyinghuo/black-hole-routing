import os
import secrets
from flask import Flask, render_template, request, redirect, Blueprint
from datetime import datetime, timedelta
from api.models import db, IpBlocklist  

blocklist_bp = Blueprint('blocklist', __name__, template_folder='templates')

@blocklist_bp.route("/", methods=["GET", "POST"])
def home():
    ips = IpBlocklist.query.all()
    if request.method == "POST":
        try:
            time_added = datetime.strptime(request.form.get("time_added"), "%Y-%m-%dT%H:%M")
            duration_hours = int(request.form.get("duration"))
            duration = timedelta(hours=duration_hours)
            time_unblocked = time_added + duration
            api_token = secrets.token_urlsafe(16)
            ip_entry = IpBlocklist(
                ip=request.form.get("ip"),
                num_blocks=int(request.form.get("num_blocks")),
                time_added=time_added,
                time_unblocked=time_unblocked,
                duration=duration,
                reason=request.form.get("reason"),
                netid=request.form.get("netid"),
                api_token=api_token
            )
            db.session.add(ip_entry)
            db.session.commit()
        except Exception as e:
            print(f"Error adding IP: {e}")
        ips = IpBlocklist.query.all()
    return render_template("home.html", ips=ips)

@blocklist_bp.route("/update", methods=["POST"])
def update():
    api_token_value = request.form.get("api_token")
    ip_entry = IpBlocklist.query.filter_by(api_token=api_token_value).first()
    if ip_entry:
        try:
            ip_entry.ip = request.form.get("ip")
            ip_entry.num_blocks = int(request.form.get("num_blocks"))
            ip_entry.time_added = datetime.strptime(request.form.get("time_added"), "%Y-%m-%dT%H:%M")
            ip_entry.time_unblocked = datetime.strptime(request.form.get("time_unblocked"), "%Y-%m-%dT%H:%M")
            ip_entry.duration = ip_entry.time_unblocked - ip_entry.time_added
            ip_entry.reason = request.form.get("reason")
            ip_entry.netid = request.form.get("netid")
            db.session.commit()
        except Exception as e:
            print(f"Error updating IP: {e}")
    return redirect("/blocklist/")

@blocklist_bp.route("/delete", methods=["POST"])
def delete():
    api_token_value = request.form.get("api_token")
    ip_entry = IpBlocklist.query.filter_by(api_token=api_token_value).first()
    if ip_entry:
        try:
            db.session.delete(ip_entry)
            db.session.commit()
        except Exception as e:
            print(f"Error deleting IP: {e}")
    return redirect("/blocklist/")
