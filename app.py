import boto3

import json

import pprint

import random

import requests

import sys

import time

##################################################################
pp = pprint.PrettyPrinter(indent=4)

with open('config.json') as f:
	config = json.load(f)

okta_rp_base_url = config["okta_rp_domain"] + "/api/v1"

okta_rp_idp_disco_policy_id = config["okta_rp_idp_disco_policy_id"]

okta_idp_base_url = config["okta_idp_domain"] + "/api/v1"

client_id = config["client_id"]

idp_max = config["idp_max"]

limit = config["batch_size_limit"]

sleep_ms = config["sleep_ms"]

##################################################################

with open('secrets.json') as f:
	secrets = json.load(f)

okta_rp_api_key = secrets["okta_rp_api_key"]

okta_idp_api_key = secrets["okta_idp_api_key"]

fake_user_password = secrets["fake_user_password"]

client_secret = secrets["client_secret"]

##################################################################

with open('idp_template.json') as f:
	data = f.read().replace('{{okta_idp_domain}}', config["okta_idp_domain"])
	data = data.replace('{{client_id}}', client_id)
	data = data.replace('{{client_secret}}', client_secret)

	idp_template = json.loads(data)

with open('routing_rule_template.json') as f:
	rule_template = json.load(f)

with open('credentials.json') as f:
	credentials = json.load(f)

	credentials["password"]["value"] = fake_user_password

##################################################################
# set up AWS client to write to dynamodb

session = boto3.Session(profile_name='dynamo_client')

boto_client = session.client('dynamodb')

##################################################################
##################################################################
# FUNCTION DEFINITIONS

def get_initial_idp_count():

	print("getting idp count from okta...")

	idp_count = 0

	done_counting = False

	headers = {
		'Authorization': "SSWS " + okta_rp_api_key,
		'Content-Type': "application/json",
		'Accept': "application/json",
		'Cache-Control': "no-cache",
		'Connection': "keep-alive",
		'cache-control': "no-cache"
	}

	while done_counting == False:

		print("*******************")

		if idp_count == 0:
			url = okta_rp_base_url + "/idps?limit=" + str(limit)

		print("starting Okta API call: list idps...")

		r = requests.get(url, headers=headers)

		if r.status_code == 200:
			print("The API call was successful.")
		else:
			print("something went wrong with the API call:")
			print(r.text)
			sys.exit()

		print("finished API call.")

		links = r.headers['Link']

		if 'rel="next"' in links:

			d = r.json()

			num_results = len(d)

			print ("the number of items returned is: %d" % num_results)

			idp_count = idp_count + num_results

			print("the idp count is now: %d" % idp_count)

			arr = links.split(',')

			url = arr[1].replace('>; rel="next"', '')

			url = url.replace(' <', '')

			time.sleep(sleep_ms / 1000)

		else:
			print('there is NOT another page.')

			done_counting = True

			return idp_count

##################################################################

def get_random_name():

	r = ''

	valid_chars = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '2', '3', '4', '5', '6', '7', '8', '9']

	for x in range(12):
		char = valid_chars[random.randint(0, len(valid_chars) - 1)]

		r = r + char

	return r

##################################################################

# def put_idp(idp_name):
def put_idp():

	idp = idp_template

	idp["name"] = idp_name

	url = okta_rp_base_url + "/idps"

	headers = {
		'Authorization': "SSWS " + okta_rp_api_key,
		'Content-Type': "application/json",
		'Accept': "application/json",
		'Cache-Control': "no-cache",
		'Connection': "keep-alive",
		'cache-control': "no-cache"
	}

	start_time = time.time()

	print("starting Okta API call: put idp...")

	r = requests.post(url, json=idp, headers=headers)

	print("finished API call.")

	end_time = time.time()

	create_idp_elapsed_time = end_time - start_time

	print("the API call took %d seconds" % int(create_idp_elapsed_time))

	if r.status_code == 200:
		print("The API call was successful.")
	else:
		print("something went wrong with the API call:")
		print(r.text)
		sys.exit()

	d = r.json()

	return d["id"]

##################################################################

def put_new_user():
	print("creating new user in okta...")

	url = okta_idp_base_url + "/users"

	email = "lois.lane@" + domain

	querystring = {"activate":"true"}

	user = {
		"profile": {
			"firstName": "Lois",
			"lastName": "Lane",
			"email": email,
			"login": email
		},
		"credentials": credentials
	}

	headers = {
		'Accept': "application/json",
		'Content-Type': "application/json",
		'Authorization': "SSWS " + okta_idp_api_key,
		'cache-control': "no-cache"
	}

	r = requests.post(url, json=user, headers=headers, params=querystring)

	if r.status_code == 200:
		print("The API call was successful.")
	else:
		print("something went wrong with the API call:")
		print(r.text)
		sys.exit()

##################################################################

def put_routing_rule(domain):

	rule = rule_template

	rule["name"] = idp_name + "_rule"

	rule["conditions"]["userIdentifier"]["patterns"][0]["value"] = domain

	rule["actions"]["idp"]["providers"][0]["id"] = idp_id

	url = okta_rp_base_url + "/policies/" + okta_rp_idp_disco_policy_id + "/rules"

	headers = {
		'Authorization': "SSWS " + okta_rp_api_key,
		'Content-Type': "application/json",
		'Accept': "application/json",
		'Cache-Control': "no-cache",
		'Connection': "keep-alive",
		'cache-control': "no-cache"
	}

	start_time = time.time()

	print("starting Okta API call: put routing rule...")

	r = requests.post(url, json=rule, headers=headers)

	print("finished API call.")

	end_time = time.time()

	create_rr_elapsed_time = end_time - start_time

	print("the API call took %d seconds" % int(create_rr_elapsed_time))

	if r.status_code == 200:
		print("The API call was successful.")
	else:
		print("something went wrong with the API call:")
		print(r.text)
		sys.exit()

##################################################################

def put_entry_in_dynamodb():
	print("pushing new IDP to dynamodb...")

	r = boto_client.put_item(
		Item={
			'idp_id': {
				'S': idp_id
			},
			'domain': {
				'S': domain
			},
			'index': {
				'N': str(index)
			},
			'create_idp_elapsed_time': {
				'N': str(int(create_idp_elapsed_time))
			},
			'create_rr_elapsed_time': {
				'N': str(int(create_rr_elapsed_time))
			},
			'okta_rp_domain': {
				'S': config["okta_rp_domain"]
			}
		},
		ReturnConsumedCapacity='TOTAL',
		TableName='idps',
	)

	if r["ResponseMetadata"]["HTTPStatusCode"] == 200:
		print("The API call was successful.")

	else:
		print("something went wrong with the API call:")
		pp.pprint(r)
		sys.exit()

##################################################################
##################################################################
# MAIN BLOCK

create_idp_elapsed_time = 0
create_rr_elapsed_time = 0

print("\n\n*************************************")

idp_count = get_initial_idp_count()

print("the initial idp count is: %d" % idp_count)

print("\n\n*************************************")

while idp_count < idp_max:

	##################################################################
	# Create new IDP in Okta

	index = idp_count + 1

	name = get_random_name()

	idp_name = str(index) + "-" + name

	idp_id = put_idp()

	print("*******************")

	##################################################################
	# Push new routing rule to okta

	domain = name + ".com"

	put_routing_rule(domain)

	print("*******************")

	##################################################################
	# Create new user in Okta IDP with same domain as new IDP in RP

	put_new_user()

	print("*******************")

	##################################################################
	# Push values to dynamodb

	put_entry_in_dynamodb()

	print("*******************")

	##################################################################

	idp_count = index

	print("there are now %d idps in the tenant" % idp_count)

	time.sleep(sleep_ms / 1000)

sys.exit()
