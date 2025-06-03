"""
Helper script to update .env file with subscription price IDs
Run this script after creating your pricing plans in Stripe
"""
import os
import sys

def update_env_file(env_path, price_ids):
    """
    Update the .env file with the Stripe price IDs for the subscription tiers.
    
    Args:
        env_path (str): Path to the .env file
        price_ids (dict): Dictionary with price IDs for each tier
    """
    # Read the current .env file
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Create a dictionary of existing env vars
    env_vars = {}
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip()
    
    # Add or update the price IDs
    env_vars['STRIPE_SOLOPRENEUR_PRICE_ID'] = price_ids.get('solopreneur', '')
    env_vars['STRIPE_ENTREPRENEUR_PRICE_ID'] = price_ids.get('entrepreneur', '')
    env_vars['STRIPE_ENTERPRISE_PRICE_ID'] = price_ids.get('enterprise', '')
    
    # Write the updated .env file
    with open(env_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print(f"Updated {env_path} with subscription price IDs")

if __name__ == "__main__":
    # Check if we're in the correct directory
    env_path = '.env'
    alternate_path = os.path.join('app', '.env')
    
    if os.path.exists(env_path):
        target_path = env_path
    elif os.path.exists(alternate_path):
        target_path = alternate_path
    else:
        print("Error: Could not find .env file. Please run this script from the project root directory.")
        sys.exit(1)
    
    # Get price IDs from command line arguments or prompt the user
    price_ids = {}
    
    if len(sys.argv) > 3:
        price_ids['solopreneur'] = sys.argv[1]
        price_ids['entrepreneur'] = sys.argv[2]
        price_ids['enterprise'] = sys.argv[3]
    else:
        print("Please enter the Stripe price IDs for each subscription tier:")
        price_ids['solopreneur'] = input("Solopreneur tier price ID: ")
        price_ids['entrepreneur'] = input("Entrepreneur tier price ID: ")
        price_ids['enterprise'] = input("Enterprise tier price ID: ")
    
    update_env_file(target_path, price_ids)
