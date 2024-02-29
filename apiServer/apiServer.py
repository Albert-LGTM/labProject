from flask import Flask, request, jsonify, abort, render_template
import requests
from jsoncomment import JsonComment
import json
from config import TAILSCALE_API_URL, TAILSCALE_API_KEY  
from flask_caching import Cache

app = Flask(__name__)

commonHeaders = {"Authorization": TAILSCALE_API_KEY}
cache = Cache(app, config={'CACHE_TYPE': 'simple'})


@app.route('/api/', methods=['GET'])
def apiUses():
    # Lists all the available endpoints of the API
    return render_template('index.html')

@cache.cached(timeout=600, key_prefix='fetchDevices')
def fetchDevices():
    response = requests.get(TAILSCALE_API_URL, headers=commonHeaders)
    response.raise_for_status()
    if response.status_code != 200:
        abort(response.status_code, message=f"Tailscale API returned an error: {response.text}")
    return response.json()["devices"]

@cache.cached(timeout=600, key_prefix='ACLData')
def getACL():
    response = requests.get("https://api.tailscale.com/api/v2/tailnet/cyberpartners.dk/acl", headers=commonHeaders)
    response.raise_for_status()
    if response.status_code != 200:
        abort(response.status_code, message=f"Tailscale API returned an error: {response.text}")

    # Need to figure out a better way to do this, but jsoncomment only accepts file
    test = response.content.decode("utf-8")
    f = open("test.txt", "w")
    f.write(test)
    f.close()
    with open("test.txt") as f:
        parser = JsonComment(json)
        data = parser.load(f)
        return data

def getAllowedGroups(userEmail, ACLData):
    userGroups = set()
    # Find all groups the user is part of
    for group, members in ACLData['groups'].items():
        if userEmail in members:
            userGroups.add(group)

    allowedTags = set()
    # Check if the user is allowed based on ACL entries
    for ACLEntry in ACLData['acls']:
        if ACLEntry['action'] == 'accept' and any(src_group in userGroups for src_group in ACLEntry['src']):
            # Extract only the tag names without ports
            filteredTags = {tag.split(':')[1] for tag in ACLEntry['dst'] if tag.startswith('tag:')}
            allowedTags.update(filteredTags)

    return allowedTags


def getUsernameByIP(IPAddress):
    try:
        response = requests.get(TAILSCALE_API_URL, headers=commonHeaders)
        response.raise_for_status()
        if response.status_code != 200:
            abort(response.status_code, message=f"Tailscale API returned an error: {response.text}")

        devices = response.json().get("devices", [])

        for device in devices:
            addresses = device.get("addresses", [])
            if IPAddress in addresses:
                return device.get("user", "Username not found")

        return "Username not found"

    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

def getTagsAndVerify(ip, ACLData):
    # gets tags of IP and then verify which tags they are allwoed to join
    try:
        devices = fetchDevices()
    except requests.exceptions.RequestException as e:
        abort(500, message=f"Failed to fetch data from Tailscale API: {e}")

    userTags = set()
    for device in devices:
        if "addresses" in device and ip in device["addresses"]:
            userTags.update(f"tag:{tag.split(':')[1]}" for tag in device.get("tags", []) if tag.startswith("tag:"))

    allowedTags = set()
    for ACLEntry in ACLData['acls']:
        if ACLEntry['action'] == 'accept' and any(src_group in userTags for src_group in ACLEntry['src']):
            # Extract only the destination tags without ports
            filteredTags = {tag.split(':')[1] for tag in ACLEntry['dst'] if tag.startswith('tag:')}
            allowedTags.update(filteredTags)

    return allowedTags

@app.route('/api/authorization/<group>/<tag>/<ip>', methods=['GET'])
def authorization(group, tag, ip):
    if not group:
        abort(400, message="Group is required")
    if not tag:
        abort(400, message="Tag is required")
    if not ip:
        abort(400, message="IP is required")

    groupList = group.split(',')
    tagList = tag.split(',')
    

    # Verify with groups
    allowedGroups = getAllowedGroups(getUsernameByIP(ip), getACL())

    if set(groupList) & allowedGroups:
        print("At least one element in groupList is equal to an element in allowedGroups")
        return jsonify({"authenticated?": True})
    else:
        app.logger.info("At least one element in groupList is equal to an element in allowedGroups")

    # Verify with tags
    allowedTags = getTagsAndVerify(ip, getACL())

    if set(tagList) & allowedTags:
        print("At least one element in tagList is equal to an element in allowedTags")
        return jsonify({"authenticated?": True})
    else:
        app.logger.info("At least one element in tagList is equal to an element in allowedTags")
    
    app.logger.info("No elements in tagList or groupList is equal to another element")
    return jsonify({"authenticated?": False})


# Legacy/unused used endpoints, remove these if ever in prod
##########################################################################################

@app.route('/api/getInfo', methods=['GET'])
def getInfo():
    query_type = request.args.get('query_type')
    query_value = request.args.get('query_value')

    if not query_type or not query_value:
        abort(400, message="Both query_type and query_value are required")

    try:
        devices = fetchDevices()
    except requests.exceptions.RequestException as e:
        abort(500, message=f"Failed to fetch data from Tailscale API: {e}")

    filterredData = [
        device for device in devices
        if (query_type == "ip" and query_value in device["addresses"]) or
           (query_type == "hostname" and query_value == device["hostname"]) or
           (query_type == "host" and query_value == device["name"]) or
           (query_type == "user" and query_value == device["user"]) or
           (query_type == "group" and query_type == device["group"])
    ]

    return jsonify({"devices": filterredData})


#Authenticate based on Hostname
@app.route('/api/authenticated', methods=['GET'])
def isAuthenticated():
    hostname = request.args.get('hostname')

    if not hostname:
        abort(400, message="Hostname is required")

    try:
        devices = fetchDevices()
    except requests.exceptions.RequestException as e:
        abort(500, message=f"Failed to fetch data from Tailscale API: {e}")

    authenticated = any(device["hostname"] == hostname for device in devices)
    return jsonify({"authenticated": authenticated})


#Authenticate based on user
@app.route('/api/user', methods=['GET'])
def getusername():
    user = request.args.get('user')

    if not user:
        abort(400, message="username is required")

    try:
        devices = fetchDevices()
    except requests.exceptions.RequestException as e:
        abort(500, message=f"Failed to fetch data from Tailscale API: {e}")

    user = any(user in device["user"] for device in devices)
    return jsonify({"user": user})


#authenticate based on IP
@app.route('/api/ipaddress', methods=['GET'])
def isIPAddressPresent():
    IPAddress = request.args.get('ip')

    if not IPAddress:
        abort(400, message="IP address is required")

    try:
        devices = fetchDevices()
    except requests.exceptions.RequestException as e:
        abort(500, message=f"Failed to fetch data from Tailscale API: {e}")

    present = any(IPAddress in device["addresses"] for device in devices)
    return jsonify({"present": present})

##########################################################################################


if __name__ == '__main__':
    app.run(host="100.79.44.107", port=4444, debug=True)

