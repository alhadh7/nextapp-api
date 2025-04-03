import requests
import base64

# Function to generate authentication token
# Function to generate authentication token
def generate_auth_token(customer_id, password, email, country_code=91):
    # Base64 encode the password
    base64_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
    
    # Prepare the URL for token generation
    url = f"https://cpaas.messagecentral.com/auth/v1/authentication/token?customerId=C-24C217810E09483&key={base64_password}&scope=NEW&country=91&email=alhadh707@gmail.com"

    headers = {
        'accept': '*/*',  # Accept all response types
    }

    try:
        # Send the GET request to generate the token (correct HTTP method)
        response = requests.get(url, headers=headers)

        # Check if the response is successful (status code 200)
        if response.status_code == 200:
            response_data = response.json()
            if response_data['status'] == 200:
                print("Token generated successfully.")
                print(f"Authentication Token: {response_data['token']}")
                return response_data['token']
            else:
                print(f"Error generating token: {response_data.get('message', 'Unknown error')}")
                return None
        else:
            print(f"Failed to generate token: {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error requesting token: {e}")
        return None


# Example usage
if __name__ == "__main__":
    # Replace these with your actual values
    customer_id = "C-24C217810E09483"  # Replace with your actual customer ID from Message Central
    password = "edgelord707"  # Your password
    email = "alhadh707@gmail.com"  # Replace with your email

    # Call the function to generate the token
    auth_token = generate_auth_token(customer_id, password, email)

    if auth_token:
        print("Successfully generated token:", auth_token)
    else:
        print("Failed to generate token.")
